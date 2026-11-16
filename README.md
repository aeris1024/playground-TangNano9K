# Tang Nano 9K FPGA Playground

Tang Nano 9KをWindows上でCLIから開発するための実験環境です。
`playground_TangPrimer25K`と同じ構成で、PowerShellを入口にPython製CLIから
シミュレーション、Gowinビルド、SRAM／内蔵Flash書き込みを行います。

## 必要なツール

- Windows、Python 3.11以上（Python標準ライブラリのみ使用）
- Gowin EDA EducationとGowin Programmer
- Icarus Verilog（`iverilog`、`vvp`）
- Tang Nano 9K、データ通信対応USB-Cケーブル

このPCでは、次のインストール済みツールを自動検出します。

| ツール | パス |
|---|---|
| Gowin EDA | `D:\Tools\Gowin\Gowin_V1.9.11.03_Education_x64\IDE\bin\gw_sh.exe` |
| Programmer | `D:\Tools\Gowin\Gowin_V1.9.11.03_Education_x64\Programmer\bin\programmer_cli.exe` |
| Icarus Verilog | `D:\Tools\iverilog\bin\iverilog.exe` |
| Icarus runtime | `D:\Tools\iverilog\bin\vvp.exe` |

別のインストール先を使う場合は、PATHまたは次の環境変数で指定します。

```powershell
$env:TANG_GOWIN_SH = 'C:\path\to\Gowin\IDE\bin\gw_sh.exe'
$env:TANG_GOWIN_PROGRAMMER = 'C:\path\to\Gowin\Programmer\bin\programmer_cli.exe'
$env:TANG_IVERILOG = 'C:\path\to\iverilog.exe'
```

`vvp.exe`は`iverilog.exe`と同じフォルダー、またはPATHから探索します。
ツール本体はリポジトリに同梱しません。

## 基本操作

このフォルダーをカレントディレクトリにして、順番に実行します。
失敗した場合は原因を解消してから次の工程へ進めます。

```powershell
.\fpga.ps1 doctor
.\fpga.ps1 list
.\fpga.ps1 sim 001_blink
.\fpga.ps1 build 001_blink
.\fpga.ps1 program 001_blink
```

- `doctor`: ツールの起動と、対象FPGAのJTAG検出を確認します。
- `sim`: 短いカウント数で周期、初期状態、LED出力極性を自己検証します。
- `build`: 合成・配置配線を実行し、`build/001_blink/001_blink.fs`を生成します。
- `program`: ビルド済みの`.fs`をSRAMへ書き込みます。自動ビルドは行いません。

実装済みデザインは次のとおりです。

| デザイン | 内容 | 検証状況 |
|---|---|---|
| `001_blink` | LED1の1 Hz点滅 | SRAM／Flashからの起動を実機確認済み |
| `002_dual_pll` | 右側のピン63/49から2基の独立PLLでADCクロックを生成 | シミュレーション・配置配線済み、実機未確認 |
| `003_analog2pdm` | PCM1808×2→独立クロックのステレオPDM×2、合計4ch | 数値・RTL・配置配線検証済み、SRAMでA/B各系統の音楽信号を実機確認 |

`004_pdm_tone`はADC迂回の内部テスト音診断です。[測定手順](designs/004_pdm_tone/README.md)を参照してください。

Analog2PDMの詳細は[デザイン説明](designs/003_analog2pdm/README.md)、
実機接続は[配線・測定手順](docs/analog2pdm_wiring.md)を参照してください。
PDM CLK Aは右側J6-1、残るDATA A／CLK B／DATA Bは隣接するJ6-19〜21です（003、2026-11-16以降）。
ビルドはsetup/hold違反数も確認し、違反がある場合は失敗します。

書き込みは`GW1NR-9C`、operation 2（SRAM Program）を使います。
FPGA名とIDCODE `0x1100481B`を事前確認し、対象を一意に検出できた場合だけ書き込みます。
複数の対象基板が接続されている場合は、`doctor`のエラーに表示されるUSB locationを
次のように指定します。この指定時も機種とIDCODEを確認します。

```powershell
$env:TANG_PROGRAMMER_LOCATION = '201745'  # この値は接続状況によって変わります
```

SRAMの内容は電源断で消えます。電源再投入後は内蔵Flashに保存されている
デザインが起動します。

## 内蔵Flashへの保存

電源を入れ直してもデザインを使いたい場合は、`--flash`を指定します。
ビルド済みの`.fs`を、FPGAの内蔵Flashへ消去・書き込みします。

```powershell
.\fpga.ps1 doctor
.\fpga.ps1 sim 001_blink
.\fpga.ps1 build 001_blink
.\fpga.ps1 program 001_blink --flash
```

`--flash`はGowin Programmerのoperation 5（`embFlash Erase,Program`）、
JTAG周波数2.5 MHzを使い、内蔵Flashの既存デザインを置き換えます。
基板上の外付けSPI Flashは対象にしません。
基板定義の`programmer_flash_operation = 5`で明示的に有効にした
`GW1NR-9C`だけに対応します。対象FPGA名とIDCODEの確認も毎回行います。

`--flash`を付けない通常の`program`は、従来どおりSRAM書き込みです。
Flash書き込みは最大300秒でタイムアウトし、ログはSRAM用と分けて保存します。
終了コード0と正常終了行`Finished.`の両方を確認し、`failed`などを含む出力は
成功として扱いません。

Flashの転送成功と、電源再投入後の起動確認は別々に記録します。
書き込み後はUSBを抜き差しし、`program`を再実行せずにLED1が
0.5秒点灯・0.5秒消灯することを確認してください。

## 001_blinkの動作

LED1（`led[0]`、FPGA pin 10）を、0.5秒点灯・0.5秒消灯の1 Hzで点滅させます。
LED2〜LED6は消灯します。外付けLEDや抵抗は不要です。

- FPGA: `GW1NR-LV9QN88PC6/I5`、device version C
- 基準クロック: 27 MHz、pin 52、LVCMOS33
- LED: pins 10 / 11 / 13 / 14 / 15 / 16、Lowで点灯
- LEDのバンク電圧: 1.8 V、LVCMOS18
- カウント数: 半周期あたり13,500,000クロック
- リセットボタンやPLLは使わず、FPGAのレジスタ初期値から開始します。

Programmerの成功は転送成功を示します。実機動作の確認には、LED1が
約1秒周期で点滅することを目視してください。

## ディレクトリ構成

```text
boards/tang_nano_9k/     デバイス、クロック、Programmerの基板定義
designs/001_blink/       design.toml、RTL、CST/SDC、自己判定付きtestbench
common/                 複数の実験で再利用する部品の置き場
tools/fpga.py           Python標準ライブラリで実装したCLI
tests/                  CLIの単体テスト
build/                  シミュレーション・ビルド・書き込みの生成物
fpga.ps1                PowerShell用の入口
```

新しい実験は`designs/<name>/design.toml`で登録します。既存のmanifestと同じ形式です。
ソースと制約のパスは設計ディレクトリ内、または`common/`だけを参照できます。

```toml
name = "001_blink"
board = "tang_nano_9k"
top = "top"
sources = ["rtl/top.sv"]
constraints = ["constraints/blink.cst", "constraints/blink.sdc"]
testbench = "sim/tb_top.sv"
```

## テストとログ

```powershell
python -m unittest discover -s tests -v
```

単体テストの一時ファイルも`build/`内に作成します。
主なログとレポートは次のとおりです。

- `build/doctor.log`: 初回構築時の診断結果
- `build/001_blink/sim/compile.log`、`sim/run.log`: シミュレーション
- `build/001_blink/build.log`: Gowinビルド
- `build/001_blink/program.log`: SRAM書き込み
- `build/001_blink/program_flash.log`: 内蔵Flashの消去・書き込み
- `build/doctor_flash.log`: Flash対応追加時の診断結果
- `build/001_blink/gowin_project/001_blink/impl/pnr/`: ピン配置・タイミングレポート

生成物の削除は`.\fpga.ps1 clean 001_blink`、全実験分は`.\fpga.ps1 clean --all`です。

## 初回構築の検証結果

2026年11月11日（日本時間）に、以下を確認しました。

| 工程 | 結果 |
|---|---|
| CLI単体テスト | 16件すべて成功 |
| doctor | 全ツール起動・対象JTAG検出成功 |
| sim | `TEST 001_blink ... PASS` |
| build | 合成・配置配線・ビットストリーム生成成功 |
| タイミング解析 | 27 MHz制約、setup/hold違反0件、Fmax 131.775 MHz |
| program | USB location 201745、SRAM Program、終了コード0・`Finished.` |
| LEDの目視 | 実機動作確認済み。LED1が0.5秒点灯・0.5秒消灯することをユーザーが確認 |

使用リソースはLogic 35、Register 25です。書き込み時の詳細は
`build/001_blink/program.log`、転送したファイルのSHA-256は
`build/001_blink/verification.json`に記録しています。

## Flash対応の検証結果

2026年11月11日（日本時間）に、CLIへFlash対応を追加し、次を確認しました。

| 工程 | 結果 |
|---|---|
| CLI単体テスト | 23件すべて成功 |
| doctor / sim / build | すべて成功。setup/hold違反0件 |
| 内蔵Flash書き込み | `embFlash Erase,Program`、終了コード0、`Program Finished!`・`Finished.` |
| 書き込み先 | `GW1NR-9C`、IDCODE `0x1100481B`、USB location 201745 |
| 電源再投入後のLチカ | Flashからの起動も実機確認済み。LED1が0.5秒点灯・0.5秒消灯することをユーザーが確認 |

Flash書き込みログは`build/001_blink/program_flash.log`、書き込んだ`.fs`の
SHA-256と検証結果は`build/001_blink/flash_verification.json`に保存しています。
Gitで管理する検証記録は`docs/verification/001_blink_flash.json`、
初回SRAM検証の記録は`docs/verification/001_blink_sram.json`です。
`build/`内の生成物やログはGitの管理対象から除外しています。
上のSRAMでの実機確認結果は、Flashからの起動確認とは区別しています。

## トラブルシュート

- ツールがMISSINGになる場合は、PATHまたは上記の環境変数を確認してください。
- JTAGが検出できない場合は、データ通信対応USBケーブル、接続、ドライバーを確認してください。
- Codexの制限環境では、Gowin Programmerがアクセス拒否になったり、Icarusの
  補助プロセスが異常終了したりする場合があります。今回の検証では、同じコマンドを
  制限外で実行して成功しています。通常のPowerShellからも実行できます。
- ログはUTF-8で保存します。外部ツールのWindows文字コード出力も処理します。

## ロードマップ

1. 開発基盤と`001_blink`（実装・シミュレーション・ビルド・SRAM書き込み・実機動作確認済み）
   内蔵Flashへの書き込みと、電源再投入後のFlashからの起動も実機確認済みです。
2. `002_dual_pll`（2基同時の配置配線と非同期クロックの機能シミュレーション済み）
3. `003_analog2pdm`（4chのRTL・数値検証・配置配線済み。A/Bの音声疎通を実機確認済み。定量評価は別途）
4. Analog2PDMの実機4ch評価、その後のFlash保存
5. ボタン入力、UART、SPI、I2Cなどの周辺回路実験

## 参考資料

- [Sipeed Tang Nano 9K](https://wiki.sipeed.com/hardware/en/tang/Tang-Nano-9K/Nano-9K.html)
- [公式LEDプロジェクト](https://github.com/sipeed/TangNano-9K-example/tree/main/led)
- [公式回路図](https://dl.sipeed.com/fileList/TANG/Nano%209K/2_Schematic/Tang_Nano_9k_3672_Schematic.pdf)

### 音質切り分けの進捗

- 004_pdm_tone: 等振幅の内部テスト音でADC以前とPDM出力経路を切り分け。内部音の実測で大きな高域減衰は再現せず、迂回したPC／ADC／I2S経路を調査。20 kHzの残留減衰は未解決。

003/004のLED3/6は音量に応じた1 kHz PWM表示と約48 msの減衰を行い、飽和・FIFO異常時には最大輝度の2 Hz点滅を優先します。

### 003のDATA出力変更（2026-11-16）

はんだ付け済みの配線に合わせ、DATA A=FPGA48 / J6-19、DATA B=FPGA31 / J6-21へ入れ替えました。
変更後、ユーザーがA/Bともに正常な音声を確認しました。004のピン割り当ては従来のままです。
今回限りのGPIO／DDR診断デザインは、確認完了後にソース・生成物・個別記録を削除しました。
