"""Bit-exact reference, numeric audio checks and standalone RTL equivalence tests.

Run from any directory. Results and generated test vectors go under build/.
NumPy is needed only for these development checks, not for tools/fpga.py.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import numpy as np

DESIGN = Path(__file__).resolve().parents[1]
ROOT = DESIGN.parents[1]
OUTPUT = ROOT / 'build/003_analog2pdm/audio'
COEFFICIENTS = json.loads((DESIGN / 'model/coefficients.json').read_text(encoding='utf-8'))
LIMIT = 1 << 23


def round_shift(value, shift):
    return (value + (1 << (shift-1)) - (value < 0)) >> shift


def halfband(pcm, stage):
    q = np.asarray(COEFFICIENTS[stage], dtype=np.int64)
    result = np.zeros(len(pcm)*2, dtype=np.int64)
    acc = np.convolve(np.asarray(pcm, dtype=np.int64), q[::2])[:len(pcm)]
    result[::2] = np.clip(round_shift(acc, 16), -LIMIT, LIMIT-1)
    delay = (len(q)-3)//4
    if len(pcm) > delay:
        result[2*delay+1::2] = pcm[:len(pcm)-delay]
    return result


def interpolate(pcm):
    pcm = np.asarray(pcm, dtype=np.int64) >> 1
    for stage in range(3):
        pcm = halfband(pcm, stage)
    return pcm


def wrap36(value):
    return ((value + (1 << 35)) & ((1 << 36)-1)) - (1 << 35)


def cic_sigma(pcm):
    pcm = [int(x) for x in pcm]
    result = np.empty(len(pcm)*8, dtype=np.uint8)
    cx = cd1 = cd2 = i1 = i2 = i3 = e1 = e2 = 0
    faults = 0
    for n in range(len(result)):
        injection = 0
        if n % 8 == 0:
            x = pcm[n//8]
            d1 = wrap36(x-cx)
            d2 = wrap36(d1-cd1)
            injection = wrap36(d2-cd2)
            cx, cd1, cd2 = x, d1, d2
        i1 = wrap36(i1+injection)
        i2 = wrap36(i2+i1)
        i3 = wrap36(i3+i2)
        sample = round_shift(i3, 6)
        if sample < -LIMIT or sample >= LIMIT:
            faults += 1
        sample = min(max(sample, -LIMIT), LIMIT-1)
        u = sample - 2*e1 + e2
        quantized = LIMIT if u >= 0 else -LIMIT
        error = quantized-u
        if error < -(1 << 31) or error >= (1 << 31):
            faults += 1
            e1 = e2 = 0
            result[n] = 0
        else:
            e1, e2 = error, e1
            result[n] = u >= 0
    return result, faults


def passband():
    f = np.linspace(20, 20000, 4001)
    response = np.ones(len(f), dtype=complex)
    fs = 48000
    for q in COEFFICIENTS:
        fs *= 2
        response *= np.exp(-2j*np.pi*f[:, None]*np.arange(len(q))/fs) @ (np.asarray(q)/65536/2)
    response *= (np.sin(np.pi*f/fs)/(8*np.sin(np.pi*f/(fs*8))))**3
    db = 20*np.log10(np.abs(response))
    db -= np.interp(1000, f, db)
    return {'min_db': float(db.min()), 'max_db': float(db.max())}


def audio_check():
    warmup, frames = 4096, 12288
    t = np.arange(warmup+frames)/48000
    results = []
    # Four independently modeled channels, including opposite polarity.
    for name, phase in zip(('A_L','A_R','B_L','B_R'), (0, 0.71, 1.39, 2.13)):
        pcm = np.rint(np.sin(2*np.pi*1000*t+phase)*10**(-6/20)*(LIMIT-1)).astype(np.int64)
        bits, faults = cic_sigma(interpolate(pcm))
        signal = bits[warmup*64:(warmup+frames)*64].astype(float)*2-1
        spectrum = np.fft.rfft(signal)
        frequency = np.fft.rfftfreq(len(signal), 1/3072000)
        fundamental = int(round(1000*len(signal)/3072000))
        band = (frequency >= 20) & (frequency <= 20000)
        band[fundamental] = False
        thdn = 10*math.log10(float(np.sum(np.abs(spectrum[band])**2))/float(abs(spectrum[fundamental])**2))
        amplitude = float(2*abs(spectrum[fundamental])/len(signal))
        results.append({'channel':name, 'thdn_db':thdn, 'output_amplitude_dbfs':20*math.log10(amplitude), 'faults':faults})
        assert faults == 0 and thdn <= -65, results[-1]
    band = passband()
    assert band['min_db'] >= -0.5 and band['max_db'] <= 0.5, band
    measured_response = []
    response_frames = 12000  # 0.25 seconds: coherent for 20 Hz, 1 kHz and 20 kHz.
    response_t = np.arange(warmup+response_frames)/48000
    for hz in (20, 1000, 20000):
        pcm = np.rint(np.sin(2*np.pi*hz*response_t)*10**(-6/20)*(LIMIT-1)).astype(np.int64)
        bits, faults = cic_sigma(interpolate(pcm))
        signal = bits[warmup*64:].astype(float)*2-1
        spectrum = np.fft.rfft(signal)
        k = int(round(hz*len(signal)/3072000))
        amplitude = 20*math.log10(float(2*abs(spectrum[k])/len(signal)))
        assert faults == 0
        measured_response.append({'hz':hz,'output_amplitude_dbfs':amplitude})
    ref = measured_response[1]['output_amplitude_dbfs']
    for row in measured_response:
        row['relative_db'] = row['output_amplitude_dbfs']-ref
        assert abs(row['relative_db']) <= 0.5
    stress = {}
    for name, pcm in {
        'silence':np.zeros(2048,dtype=np.int64),
        'positive_full_scale':np.full(2048,LIMIT-1,dtype=np.int64),
        'negative_full_scale':np.full(2048,-LIMIT,dtype=np.int64),
        'full_scale_step':np.repeat(np.array([0,LIMIT-1,-LIMIT,0],dtype=np.int64),1024),
        'impulse':np.r_[np.array([LIMIT-1],dtype=np.int64),np.zeros(2047,dtype=np.int64)]
    }.items():
        bits, faults = cic_sigma(interpolate(pcm))
        assert faults == 0, name
        density = float(np.mean(bits[1024*64:]))
        if name == 'silence': assert abs(density-0.5) < 0.001
        if name == 'positive_full_scale': assert abs(density-0.75) < 0.001
        if name == 'negative_full_scale': assert abs(density-0.25) < 0.001
        stress[name]={'faults':faults,'settled_density':density}
    return {'passband_20hz_20khz':band, 'bit_exact_model_response':measured_response,
            'stress':stress, 'tone_hz':1000, 'input_dbfs':-6, 'gain_db':20*math.log10(0.5),
            'measurement_band_hz':[20,20000], 'channels':results, 'status':'PASS'}


def tools():
    spec = importlib.util.spec_from_file_location('fpga_audio_check', ROOT/'tools/fpga.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.require_tool('iverilog'), module.require_tool('vvp')


def run_rtl(tb, name, sources):
    iverilog, vvp = tools()
    path = OUTPUT / f'{name}.sv'
    path.write_text(tb, encoding='utf-8')
    executable = OUTPUT / f'{name}.vvp'
    commands = [[str(iverilog), '-g2012', '-s', 'tb', '-o', str(executable), *map(str,sources), str(path)],
                [str(vvp), str(executable)]]
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=120)
        output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
        (OUTPUT/f'{name}_{index}.log').write_text(output, encoding='utf-8')
        if result.returncode:
            raise RuntimeError(output or f'{name}: exit code {result.returncode}')
        if output:
            print(output.strip())


def rtl_check():
    rng = np.random.default_rng(1808)
    frames = 192
    # Bounded random samples and exact endpoints exercise sign and rounding.
    pcm = rng.integers(-LIMIT//2, LIMIT//2, (frames,2), dtype=np.int64)
    pcm[:8] = np.array([[0,0],[1,-1],[-1,1],[LIMIT//2-1,-LIMIT//2],[0,0],[127,-127],[32768,-32768],[0,0]])
    for stage, period in enumerate((256,128,64)):
        expected = np.column_stack([halfband(pcm[:,ch],stage) for ch in range(2)])
        input_path = OUTPUT/f'fir{stage}_input.hex'
        expect_path = OUTPUT/f'fir{stage}_expected.hex'
        for path, data in ((input_path,pcm),(expect_path,expected)):
            path.write_text(''.join(f'{int(l)&0xffffff:06x}{int(r)&0xffffff:06x}\n' for l,r in data),encoding='utf-8')
        tb = f'''`timescale 1ns/1ps
module tb;
reg clk=0, reset=1, valid=0;
reg signed [23:0] l=0,r=0;
wire v, clip; wire signed [23:0] ol,orr;
reg [47:0] input_data[0:{frames-1}], expected[0:{frames*2-1}];
integer n, result_count=0;
always #5 clk=~clk;
halfband_stereo #(.STAGE({stage}),.TAPS({len(COEFFICIENTS[stage])}),.PERIOD({period})) dut
(.clk(clk),.reset(reset),.in_valid(valid),.in_l(l),.in_r(r),.out_valid(v),.out_l(ol),.out_r(orr),.clipped(clip));
always @(negedge clk) if(v) begin
 if ({{ol,orr}} !== expected[result_count]) $fatal(1,"FIR{stage} mismatch n=%0d actual=%h expected=%h",result_count,{{ol,orr}},expected[result_count]);
 result_count=result_count+1;
end
initial begin
 $readmemh("{input_path.as_posix()}",input_data);
 $readmemh("{expect_path.as_posix()}",expected);
 repeat(3) @(negedge clk); reset=0;
 for(n=0;n<{frames};n=n+1) begin
  {{l,r}}=input_data[n]; valid=1;
  @(negedge clk); valid=0;
  repeat({period-1}) @(negedge clk);
 end
 repeat({period}) @(negedge clk);
 if(result_count!={frames*2} || clip) $fatal(1,"FIR{stage} count or clip");
 $display("TEST FIR{stage} bit-exact ... PASS"); $finish;
end
endmodule
'''
        run_rtl(tb,f'fir{stage}',[DESIGN/'rtl/halfband_stereo.sv',DESIGN/'rtl/halfband_coeff.sv'])
    data = pcm[:,0]
    expected, faults = cic_sigma(data)
    assert faults == 0
    input_path=OUTPUT/'cic_input.hex'; expect_path=OUTPUT/'cic_expected.hex'
    input_path.write_text(''.join(f'{int(x)&0xffffff:06x}\n' for x in data),encoding='utf-8')
    expect_path.write_text(''.join(f'{int(x):x}\n' for x in expected),encoding='utf-8')
    tb=f'''`timescale 1ns/1ps
module tb;
reg clk=0,reset=1,valid=0; reg signed[23:0] pcm=0;
wire pdm,clip;
reg[23:0] inputs[0:{frames-1}]; reg expected[0:{frames*8-1}];
integer n;
always #5 clk=~clk;
cic_sigma dut(.clk(clk),.reset(reset),.input_valid(valid),.pcm(pcm),.pdm(pdm),.clipped(clip));
initial begin
 $readmemh("{input_path.as_posix()}",inputs); $readmemh("{expect_path.as_posix()}",expected);
 repeat(3) @(negedge clk); reset=0;
 for(n=0;n<{frames*8};n=n+1) begin
  valid=n%8==0; pcm=inputs[n/8]; @(posedge clk); #1;
  if(pdm!==expected[n] || clip) $fatal(1,"CIC/sigma mismatch n=%0d",n);
  @(negedge clk);
 end
 $display("TEST CIC/sigma bit-exact ... PASS"); $finish;
end
endmodule
'''
    run_rtl(tb,'cic_sigma',[DESIGN/'rtl/cic_sigma.sv'])
    input_path=OUTPUT/'i2s_input.hex'
    input_path.write_text(''.join(f'{int(l)&0xffffff:06x}{int(r)&0xffffff:06x}\n' for l,r in pcm),encoding='utf-8')
    tb=f'''`timescale 1ns/1ps
module tb;
reg clk=0,reset=1; reg [7:0] phase=0;
reg [23:0] wl=0,wr=0; reg data=0;
wire valid; wire signed[23:0] l,r;
reg[47:0] words[0:{frames-1}];
reg signed[23:0] expected_l,expected_r;
integer n,slot,result_count=0;
always #5 clk=~clk;
always @(posedge clk) if(reset) phase<=0; else phase<=phase+1'b1;
always @(negedge clk) begin
 slot=phase[6:2];
 data=(slot>=1 && slot<=24) ? (phase[7] ? wr[24-slot] : wl[24-slot]) : 1'b1;
 if(valid) begin
  expected_l=$signed(words[result_count][47:24])>>>1;
  expected_r=$signed(words[result_count][23:0])>>>1;
  if(l!==expected_l || r!==expected_r) $fatal(1,"I2S bit-exact mismatch n=%0d",result_count);
  result_count=result_count+1;
 end
end
i2s_receive dut(.clk(clk),.reset(reset),.ready(1'b1),.adc_data(data),.phase(phase),.sample_valid(valid),.pcm_l(l),.pcm_r(r));
initial begin
 $readmemh("{input_path.as_posix()}",words);
 repeat(3) @(negedge clk); #1; reset=0;
 for(n=0;n<{frames};n=n+1) begin
  {{wl,wr}}=words[n]; repeat(256) @(negedge clk); #1;
 end
 if(result_count!={frames}) $fatal(1,"I2S frame count");
 $display("TEST I2S random stereo bit-exact ... PASS"); $finish;
end
endmodule
'''
    run_rtl(tb,'i2s',[DESIGN/'rtl/i2s_receive.sv'])
    return {'fir_stages':3,'stereo_frames_per_stage':frames,'i2s_stereo_frames':frames,
            'cic_sigma_bits':frames*8,'status':'PASS'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rtl',action='store_true',help='also run bit-exact Icarus tests')
    parser.add_argument('--rtl-only',action='store_true')
    args=parser.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    result={}
    if not args.rtl_only:
        result['audio']=audio_check()
        print(json.dumps(result['audio'],indent=2))
    if args.rtl or args.rtl_only:
        result['rtl']=rtl_check()
    (OUTPUT/('rtl_results.json' if args.rtl_only else 'results.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('TEST audio verification ... PASS')
