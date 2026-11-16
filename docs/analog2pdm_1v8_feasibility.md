# Analog2PDMの1.8 V対応検討（2026-11-16）

## 結論と確認範囲

PDMのCLK/DATAだけを1.8 Vバンクへ移す別デザインは実現可能と判断します。
build/feasibility_1v8内の一時試作で003と同じ全音声回路を合成・配置配線し、
2/2 PLL、LVCMOS18の4端子、setup/hold違反0件を確認しました。
正式デザイン005_analog2pdm_1v8を追加しました。既存003のソースは変更していません。
調査時には書き込まず、その後の明示依頼により最終試作をSRAMへ転送しました（末尾参照）。
同一回路の試作で両系統のLOCK・処理開始・音声受信は実機確認済みです。停止復帰・波形の定量評価は別途確認です。

## 仮ピン割り当て

USB-Cを上にした部品面から見た右側ヘッダーJ6です。

| 信号 | FPGA物理ピン | ヘッダー |
|---|---:|---|
| PDM CLK A | 85 | J6-3 |
| PDM DATA A | 84 | J6-4 |
| PDM CLK B | 83 | J6-5 |
| PDM DATA B | 82 | J6-6 |
| 共通GND | — | J6-23など |

4信号ともバンク3、LVCMOS18、VCCIO=1.8 Vです。ADCのMCLK/BCLK/LRCLK/DOUTは3.3 Vのままです。
SPI/RGB LCDとの併用は避けます。基板LEDと同じ1.8 Vバンクですが、LEDの割り当ては維持できます。
ピン85/83は専用クロックピンではありません。一般配線からPLL/グローバル配線へ接続できましたが、
PR1014の警告は残ります。オシロでの入力波形とPLL LOCKの実機検証が必要です。

## 電圧とクロック

1.8 Vは外部I/Oバッファの電圧で、PLLが1.8 V振幅を直接扱う構成ではありません。
LVCMOS18の入力条件はVIH>=0.65×VCCIO、VIL<=0.35×VCCIOです（VCCIO=1.8 Vなら1.17/0.63 V）。
相手のVOH/VOL・負荷とsetup/hold条件も確認します。
外部クロックは従来と同じ公称3.072 MHz、各系統4倍の12.288 MHzとします。
44.1 kHz×64=2.8224 MHzのPLL下限問題は電圧変更では解消しません。
相手の1.8 V入力に現行3.3 V DATA出力を直結しません。機器間はGNDを共通にし、電源レール同士は接続しません。

## リセットの修正が必要

CSTだけ移した初回試験では、PLL由来のreadyから元のPDMクロック領域に渡るリセット経路にhold違反18件が出ました。
FIFOのwrite_resetとread_resetを分け、後者を既存の3段read_releaseで同期解除すると3件になりました。
残る3件はread_release同期回路自身の非同期CLEAR入力でした。
SDCで両系統のread_release*/CLEARだけを例外に指定し、setup/hold違反0件となりました。
FIFOデータ・通常レジスター・同期段間のD経路の解析は残しています。
この修正は一時試作だけです。正式実装時に別デザインへ取り込み、シミュレーションとタイミングを再確認します。

## 3.3 Vとの切り替え案

1. 最初は現行003を残し、1.8 V専用デザインを追加する方針を推奨します。
2. 将来は1.8 Vと3.3 Vで別々の固定電圧端子を用意し、外付けスイッチ入力で選択する構成を検討できます。
   選択入力は起動時に取り込み、ミュート・PLLリセット・再LOCK後に開始する方式が扱いやすいです。
   クロック選択回路、出力セル追加、非選択端子の扱い、配置配線は未検証です。無瞬断切り替えは前提にしません。
3. 同じFPGA端子の電圧をスイッチやRTLで1.8/3.3 Vへ切り替える方式は採用しません。
   基板のバンク電源は固定で、バンク3にはLED/JTAG等も接続されています。
4. 別案として、現行3.3 Vの4信号に方向固定の外付けレベル変換を入れる方法もあります。
   CLKは1.8→3.3 V、DATAは3.3→1.8 Vで、遅延・波形・受信余裕の評価が必要です。

## 残る確認

- 相手は1.8 V CMOSの公称3.072 MHzクロックをA/B独立で出すか。
- PDM取り込みエッジは従来と同じL=立ち下がり/R=立ち上がりか。
- 端子の電圧規格、クロック停止/再開、電源OFF時の端子状態、配線長。
- 実機の1.8 V入力、両PLL LOCK、DATA振幅・エッジ余裕、4ch音声。

## 根拠資料

- [Sipeed公式回路図](https://dl.sipeed.com/fileList/TANG/Nano%209K/2_Schematic/Tang_Nano_9k_3672_Schematic.pdf)
- [Sipeed配布のGW1NRデータシート（LVCMOS18、I/O DC特性）](https://dl.sipeed.com/fileList/TANG/Nano%209K/6_Chip_Manual/EN/DS117-2.9.3E_GW1NR%20series%20of%20%20FPGA%20Products%20DataSheet.pdf)
- [Gowin Clock User Guide](https://cdn.gowinsemi.com.cn/UG286E.pdf)
- ローカルGowinのGW1NR-9C/QFN88Pピン定義、一時プロジェクトの配置配線・タイミングレポート。

## SRAM試験開始（2026-11-16）

ユーザーの明示依頼により、gowin_project_cdc/probe_1v8_cdc/impl/pnr/probe_1v8_cdc.fsを転送しました。
同期リセット修正とCDC例外適用後のsetup/hold違反0件の版です。
GW1NR-9C、ID=0x1100481B、USB=201745を確認し、SRAM Programの終了コード0とFinished.を確認しました。
Flashは変更していません。ユーザーがLED1/2/4/5の点灯とA/B両方の音声受信を確認しました。
転送ログとbitstreamのハッシュはbuild/feasibility_1v8/results.jsonおよびprogram_sram.logに記録しています。

## 正式登録（2026-11-16）

試作と同一のRTL/CST/SDCを005_analog2pdm_1v8として登録しました。
正式デザインの検証記録はdocs/verification/005_analog2pdm_1v8.jsonに保存します。
実機にロードした試作と正式名で再ビルドしたbitstreamのハッシュは区別して記録します。
