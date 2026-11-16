# Analog2PDM 配線・測定手順

この手順は`003_analog2pdm`向けです。現在はADCとMCHStreamerが未配線で、
ソフトウェアの検証とビットストリーム生成まで完了しています。

## 接続するもの

- Tang Nano 9K
- Youmile PCM1808基板2枚（Amazon ASIN B09BTLPBM4）
- PDMファームウェアのMCHStreamer KitまたはLite、48 kHz設定
- 4ch以上の入力を録音できるASIO対応ソフト、音声信号源
- クロックとデータ波形を確認できるオシロスコープまたはロジックアナライザー

以下のTang側の番号は**FPGAの物理ピン番号**です。コネクターの何番目かを表す番号ではありません。
ボード上の番号表示と公式ピン図で対応を確認してください。
信号はすべて3.3 Vで、1.8 Vバンクのヘッダーピンは使いません。

## 電源とモード設定

両方のUSB電源を切って配線します。ADCは1枚ずつ確認してから2枚接続します。

| Tang Nano 9K | PCM1808 A/B |
|---|---|
| 5 V（公式回路図 J6-18） | 各基板の5V |
| 3.3 V（J6-24） | 各基板の3.3V |
| GND（J6-23など） | 各基板のGND |

PCM1808基板にはアナログ5 Vとデジタル3.3 Vを両方供給します。
`MD0`、`MD1`、`FMY/FMT`はLow（GND）に設定します。
`FMY`表記の端子は、実物でPCM1808のFMT端子に接続されていることを確認してください。
MCHStreamerとはGNDを共通にし、MCHStreamer J3-2の3.3 V出力はTangの電源へ接続しません。

## ADC信号

| Tang信号 | Aの物理ピン | Bの物理ピン | PCM1808側 | 方向 |
|---|---:|---:|---|---|
| ADC MCLK | 25 | 29 | SCK（SCKI） | FPGA→ADC |
| ADC BCLK | 26 | 30 | BCK | FPGA→ADC |
| ADC LRCLK | 27 | 33 | LRC（LRCK） | FPGA→ADC |
| ADC DATA | 28 | 34 | OUT（DOUT） | ADC→FPGA |

アナログのL/Rは各基板のLIN/RIN、信号源のGNDは基板のアナログ入力側GNDへ接続します。
基板の入力回路に合わせたライン信号を使います。マイク用プリアンプはこの設計に含みません。

## MCHStreamer信号

以下は2026-11-16以降の003専用です。004のDATA A/Bはこの表と逆です。

| MCHStreamer J3 | Tang Nano 9K | 方向 |
|---|---|---|
| 11: PDM CLK | J6-1 / FPGA 63: PDM_CLK A | MCH→FPGA |
| 12: PDM CLK2 | J6-20 / FPGA 49: PDM_CLK B | MCH→FPGA |
| 3: PDM 1-2 | J6-19 / FPGA 48: PDM_DATA A | FPGA→MCH |
| 4: PDM 3-4 | J6-21 / FPGA 31: PDM_DATA B | FPGA→MCH |
| 1: GND | J6-23 / GND | 共通 |

2026-11-13にPDMの4信号を右側ヘッダーJ6へ集約しました。
向きはUSB-Cを上にした部品面視点です。旧配線のB CLK=35、A DATA=41、B DATA=42は使用しません。
ピン31/48/49はLCD信号と共用なので、SPI LCDやRGB LCDは併用しないでください。
ADC側のピン割り当ては変更ありません。

J3は2 mmピッチです。向きとpin 1を確認し、信号線は短くしてください。
PDMはLを立ち下がり、Rを立ち上がりで取り込みます。

## 初回の確認

1. ADCの電源端子とモード設定を実物で確認します。2枚とも、端子・部品実装とクロック／データ波形を個別に確認します。
2. MCHStreamerをPDMファームウェア・48 kHzに設定し、J3-11/12に3.072 MHzが出ていることを確認します。
3. ADC Aの信号線から接続し、次を順に実行します。

```powershell
.\fpga.ps1 doctor
.\fpga.ps1 sim 003_analog2pdm
.\fpga.ps1 build 003_analog2pdm
.\fpga.ps1 program 003_analog2pdm
```

4. LED1（A LOCK）、LED2（A処理開始）が点灯し、LED3（A音声／異常）が点滅していないことを確認します。起動待ちは250 msです。Bにクロックを接続していればBの状態LEDも動作します。
5. ADC A側でMCLK=12.288 MHz、BCLK=3.072 MHz、LRCLK=48 kHz、DOUTを確認します。MCLKのデューティ、LRCLKのsetup/hold、PDMの両取り込みエッジ前後の余裕も測定します。
6. Lだけに1 kHzを入力してUSB ch1、Rだけに入力してch2へ現れることを確認します。
7. 電源を切ってADC Bを接続し、同様にBのL→ch3、R→ch4を確認します。
8. 4ch同時録音を行い、左右の分離、LED3/6が点滅しないこと、連続動作を確認します。
9. 各系統のクロック線だけを外した場合に、その系統が停止し、他方の録音が続くことを確認します。復帰後は再度250 ms以上待って確認します。

片系の配線を省略するときは、そのADC DATA入力をGNDへ固定して浮かせないでください。
Flashにはまだ書き込まず、まずSRAMで検証します。

## 音質と独立性の記録

ADC A/L、A/R、B/L、B/Rへ同じ基準レベルを順に入力し、24 bit・48 kHzの録音を保存します。
20 Hz、1 kHz、20 kHzの振幅と、1 kHz時のTHD+Nを測定します。
THD+Nの帯域は20 Hz〜20 kHz、非重み付け、DC除外とし、入力レベルも記録します。
FPGAの既定利得は−6.0206 dBです。ADC基板のアナログ利得とMCHStreamerのデシメーション応答は別に評価します。

数値モデルの±0.5 dB／−65 dBはFPGA変換部の基準です。
ADC基板・電源・配線・MCHStreamerを含む実測値を、モデルの結果に置き換えて報告しないでください。
特にADC基板だけの周波数応答を先に確認し、アナログ入力回路の問題を切り分けます。

MCHStreamer 1台のCLKとCLK2は同じクロックなので、独立周波数の実機試験は未確認として残します。
独自デバイスや2台目の受信機を用意した後、A/Bの周波数を別々にして確認します。

4ch録音を確認できた後に限り、必要に応じて次のコマンドでFlashへ保存します。

```powershell
.\fpga.ps1 program 003_analog2pdm --flash
```

## 参考資料

- [PCM1808データシート](https://www.ti.com/lit/ds/symlink/pcm1808.pdf)
- [MCHStreamer User Manual（PDM設定とJ3配線）](https://www.minidsp.com/images/documents/MCHStreamer%20User%20Manual.pdf)
- [Tang Nano 9K公式回路図](https://dl.sipeed.com/fileList/TANG/Nano%209K/2_Schematic/Tang_Nano_9k_3672_Schematic.pdf)
- [対象PCM1808基板](https://www.amazon.co.jp/dp/B09BTLPBM4)

2026-11-14: PDM DATA AをFPGAピン77（J6-10）から31（J6-21）へ移しました。
PDM DATA B／CLK B／DATA AはJ6-19／20／21の隣接した3端子です。
PDM CLK AはFPGAピン63（J6-1）のままです。ADC信号は変更していません。

## 端子番号の訂正（2026-11-14）

以前のJ6-18〜20という案内は誤りでした。USB-C側を1とした右側ヘッダーは、
J6-18が5 V、J6-19がFPGAピン48（DATA B出力）、J6-20がピン49（CLK B入力）、
J6-21がピン31（DATA A出力）、J6-22がピン32、J6-23がGND、J6-24が3.3 Vです。
電源を切ってBクロックをJ6-20へ接続し直してください。ADCの5 V電源端子もJ6-18か確認してください。
FPGA物理ピン番号とCSTの割り当ては変更ありません。

## 実機疎通確認（2026-11-14）

正しい端子位置へ接続後、ユーザーがA/Bで合計4個のLED点灯を確認しました。
PCの音楽をADC Aへ入力してASIO上で音声らしい波形を確認し、
同じ音源をADC Bへ移した場合も音楽信号らしい波形を確認しました。
SRAMで両系統の基本疎通を確認済みです。左右個別対応、定量的な音質、長時間安定性、Flash起動は別途確認します。

PWM音量表示追加後は、LED3/6の明るさは音量を表す正常な表示です。異常は最大輝度の2 Hz点滅で表示します。

## 現在のDATA配線（2026-11-16改訂・003のみ）

003はDATA A=J6-19 / FPGA48、DATA B=J6-21 / FPGA31です。
2026-11-14の端子番号訂正の節は当時の信号割り当てであり、現在の003には適用しません。
ヘッダーの物理位置と5 V/GND/3.3 Vの位置は変更していません。
004はDATA A=J6-21 / FPGA31、DATA B=J6-19 / FPGA48です。診断デザインと003を切り替えるとDATAのA/B対応が変わります。

2026-11-16、DATA出力入れ替え後にユーザーがA/Bともに正常な音声を確認しました。
Flashからの起動確認とは別の、SRAM動作の確認です。
