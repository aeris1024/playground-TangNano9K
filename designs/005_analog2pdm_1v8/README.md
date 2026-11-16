# 005_analog2pdm_1v8

PCM1808×2の合計4chを、独立した2系統の1.8 V PDMへ変換します。
003は3.3 V版として残し、本デザインではPDMのCLK/DATAだけをバンク3のLVCMOS18へ移しています。
ADC側の信号と電源は従来どおりです。音声処理とLEDの仕様は003を引き継ぎます。

## 実機確認

2026-11-16、同一RTL/CST/SDCの試作をSRAMに転送し、Programmerの終了コード0とFinished.を確認しました。
ユーザーがLED1/2/4/5の点灯、およびA/Bともに音声を受信できることを確認済みです。
正式登録後の再ビルドと、実機確認した試作bitstreamのハッシュは検証記録で区別しています。
正式名で再ビルドしたbitstream自体は再転送していません。Flash保存・電源再投入後の起動は未確認です。

## PDM端子

USB-Cを上にした部品面から見て右側ヘッダーを上から数えます。

| 信号 | FPGA物理ピン | ヘッダー | 電圧・方向 |
|---|---:|---|---|
| PDM CLK A | 85 | J6-3 | 1.8 V入力 |
| PDM DATA A | 84 | J6-4 | 1.8 V出力 |
| PDM CLK B | 83 | J6-5 | 1.8 V入力 |
| PDM DATA B | 82 | J6-6 | 1.8 V出力 |
| GND | — | J6-23など | 相手機器と共通 |

公称3.072 MHz（48 kHz×64）専用です。A/Bは独立して動作します。
3.3 V版003とはPDM接続先が異なります。1.8 V機器に003の3.3 V DATA出力を接続しないでください。
機器間はGNDを共通にし、電源レール同士は接続しません。SPI/RGB LCDとの併用は避けます。
左右の取り込みはL=立ち下がり、R=立ち上がり。SWAP_EDGES_A/Bの合成時設定で変更できます。

## PCM1808側（3.3 V信号）

| 信号 | AのFPGAピン | BのFPGAピン | ADC端子 |
|---|---:|---:|---|
| MCLK | 25 | 29 | SCK / SCKI |
| BCLK | 26 | 30 | BCK |
| LRCLK | 27 | 33 | LRC / LRCK |
| DOUT入力 | 28 | 34 | OUT / DOUT |

MCLK=12.288 MHz、BCLK=3.072 MHz、LRCLK=48 kHzです。
MD1/MD0/FMTはLowにし、ADCにはアナログ5 Vとデジタル3.3 Vを供給します。
Tangの電源を使う場合はJ6-18=5 V、J6-24=3.3 V、J6-23=GNDです。
対象基板の入力コンデンサ問題など、アナログ品質の課題は電圧版の変更とは別です。

## 起動・音声処理・LED

PLL LOCK後、同期リセット解除と250 ms待ちを経て処理開始します。停止は該当系統だけをリセットします。
24 bit I2S→1/2利得→半帯域FIR×8→FIFO→CIC×8→2次ΔΣ→DDRの構成です。
FIR/CIC/ΔΣの数値検証は[003のモデル](../003_analog2pdm/model/verify_audio.py)を参照してください。

- LED1/4: A/BのPLL LOCK。
- LED2/5: A/Bの処理開始。
- LED3/6: L/Rの大きい方の音量を1 kHz PWM表示。約−60〜0 dBFSの対数31段階。
- 音量表示は素早く立ち上がり、全輝度から無音まで約48 msで減衰。飽和/FIFO異常時は最大輝度の2 Hz点滅を優先。

## 003からのリセット変更

1.8 V端子への移動で生じたクロック配線差に対応し、FIFOのwrite_resetとread_resetを分離しました。
read_resetは元のPDMクロックで3段同期して解除します。
SDCはread_release同期回路自身のCLEAR端子だけを非同期リセット例外に指定します。
既存のGrayポインター第1同期段例外に加えるもので、同期段間やFIFOデータは解析対象に残します。
PR1014（一般配線によるクロック接続）の警告は残り、LOCKと音声受信までの実機確認を行っています。
アナログ音質、ジッタ、両エッジのタイミング余裕の定量保証とは別です。

## CLI

```powershell
.\fpga.ps1 doctor
.\fpga.ps1 sim 005_analog2pdm_1v8
.\fpga.ps1 build 005_analog2pdm_1v8
.\fpga.ps1 program 005_analog2pdm_1v8
```

自己判定テストは符号/I2S遅延、4ch PDM密度、エッジ交換、±1000 ppm、片系停止復帰、非対応周波数ミュート、PWM音量表示を確認します。
既定のprogramはSRAMのみです。3.3/1.8 Vのスイッチ選択や自動電圧判定は実装していません。

[検証記録](../../docs/verification/005_analog2pdm_1v8.json)・[調査経緯](../../docs/analog2pdm_1v8_feasibility.md)
