# TM1121 BLE Measurement on Windows

A&D製パルスオキシメータ **TM1121** から、Windows PCへBluetooth Low Energy（BLE）経由で
SpO₂と脈拍数を取得し、CSVへ保存するための手順です。

このREADMEは、以下の動作確認結果をもとに作成しています。

- デバイス名: `TM1121`
- BLE Service UUID: `23444100-9c95-1740-a38a-000bdb712c7c`
- Notify Characteristic UUID: `23444102-9c95-1740-a38a-000bdb712c7c`
- 受信データの3バイト目: SpO₂
- 受信データの5バイト目: 脈拍数

> 注意: Pythonでは配列の添字が0から始まるため、
> 「3バイト目」は `data[2]`、「5バイト目」は `data[4]` です。

---

## 1. 必要なもの

- Windows PC
- Bluetooth Low Energy対応Bluetoothアダプタ
- A&D TM1121
- TM1121用SpO₂センサ
- Python 3.10以降を推奨
- Pythonライブラリ `bleak`

---

## 2. TM1121側の準備

TM1121は **M（Monitoring）モード** にします。

1. TM1121の電源をOFFにする
2. 背面のモードスイッチを `M` にする
3. SpO₂センサを接続する
4. 指をセンサに装着する
5. 測定ボタンを押して測定を開始する
6. 本体画面にSpO₂と脈拍数が表示されることを確認する

Bluetooth未接続時は橙色LEDがゆっくり点滅します。

---

## 3. WindowsでBluetoothペアリング

Windowsの

`設定` → `Bluetoothとデバイス`

からBluetoothをONにします。

TM1121が表示された場合は、通常のBluetoothデバイスと同様にペアリングします。

確認済みのデバイス情報の例:

```text
Name    : TM1121
Address : 4C:24:98:4D:03:0E
Services: ['23444100-9c95-1740-a38a-000bdb712c7c']
```

MACアドレスは個体ごとに異なる可能性があるため、本READMEのプログラムでは
原則としてMACアドレスを固定せず、Service UUIDまたはデバイス名から検索します。

---

## 4. Python環境の作成

PowerShellを開き、作業用ディレクトリを作成します。

```powershell
mkdir tm1121_test
cd tm1121_test
```

仮想環境を作成します。

```powershell
py -m venv .venv
```

仮想環境を有効化します。

```powershell
.\.venv\Scripts\Activate.ps1
```

PowerShellの実行ポリシーでエラーになる場合は、必要に応じて以下を実行します。

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

`bleak` をインストールします。

```powershell
python -m pip install --upgrade pip
python -m pip install bleak
```

確認:

```powershell
python -m pip show bleak
```

---

# 5. BLEスキャン

まず、TM1121がPCから見えていることを確認します。

`scan.py` を作成します。

```python
import asyncio
from bleak import BleakScanner


async def main():
    print("BLEデバイスを10秒間スキャンします...\n")

    devices = await BleakScanner.discover(
        timeout=10.0,
        return_adv=True,
    )

    for _, (device, adv) in devices.items():
        print("=" * 60)
        print(f"Name    : {device.name}")
        print(f"Address : {device.address}")
        print(f"RSSI    : {adv.rssi}")
        print(f"Local   : {adv.local_name}")
        print(f"Services: {adv.service_uuids}")


if __name__ == "__main__":
    asyncio.run(main())
```

実行:

```powershell
python scan.py
```

以下のような出力が確認できればOKです。

```text
Name    : TM1121
Address : 4C:24:98:4D:03:0E
RSSI    : -48
Local   : TM1121
Services: ['23444100-9c95-1740-a38a-000bdb712c7c']
```

---

# 6. GATT Service / Characteristicの確認

TM1121では、以下の独自Serviceが確認されています。

```text
23444100-9c95-1740-a38a-000bdb712c7c
```

Characteristicは以下です。

```text
23444101-9c95-1740-a38a-000bdb712c7c  read, indicate
23444102-9c95-1740-a38a-000bdb712c7c  read, notify
23444103-9c95-1740-a38a-000bdb712c7c  read, write
23444104-9c95-1740-a38a-000bdb712c7c  read, write
23444105-9c95-1740-a38a-000bdb712c7c  read, write
23444106-9c95-1740-a38a-000bdb712c7c  read, write
23444107-9c95-1740-a38a-000bdb712c7c  read, write
```

測定値取得には、現時点では以下のNotify Characteristicを使用します。

```text
23444102-9c95-1740-a38a-000bdb712c7c
```

---

# 7. TM1121の自動検出 + 測定値表示 + CSV保存

`record_tm1121.py` を作成します。

```python
import asyncio
import csv
from datetime import datetime
from pathlib import Path

from bleak import BleakClient, BleakScanner


SERVICE_UUID = "23444100-9c95-1740-a38a-000bdb712c7c"
NOTIFY_UUID = "23444102-9c95-1740-a38a-000bdb712c7c"

CSV_FILE = Path("tm1121_data.csv")


async def find_tm1121():
    print("TM1121を検索しています...")

    devices = await BleakScanner.discover(
        timeout=10.0,
        return_adv=True,
    )

    # Service UUIDを最優先で判定
    for _, (device, adv) in devices.items():
        service_uuids = [
            uuid.lower()
            for uuid in (adv.service_uuids or [])
        ]

        if SERVICE_UUID.lower() in service_uuids:
            print("TM1121をService UUIDから発見しました。")
            return device

    # Service UUIDが広告されなかった場合は名前で判定
    for _, (device, adv) in devices.items():
        names = [
            device.name,
            adv.local_name,
        ]

        if any(
            name is not None and "TM1121" in name.upper()
            for name in names
        ):
            print("TM1121をデバイス名から発見しました。")
            return device

    return None


def write_header_if_needed():
    if CSV_FILE.exists() and CSV_FILE.stat().st_size > 0:
        return

    with CSV_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "spo2",
                "pulse",
                "raw_hex",
            ]
        )


def notification_handler(sender, data: bytearray):
    # SpO2=data[2], Pulse=data[4] のため最低5 byte必要
    if len(data) < 5:
        print(
            f"短いデータを受信したため無視しました: "
            f"{data.hex(' ')}"
        )
        return

    spo2 = data[2]
    pulse = data[4]

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )[:-3]

    raw_hex = data.hex(" ")

    print(
        f"{timestamp}  "
        f"SpO2={spo2}%  "
        f"Pulse={pulse} bpm"
    )

    with CSV_FILE.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                timestamp,
                spo2,
                pulse,
                raw_hex,
            ]
        )


async def main():
    write_header_if_needed()

    device = await find_tm1121()

    if device is None:
        print("")
        print("TM1121が見つかりませんでした。")
        print("以下を確認してください。")
        print("- TM1121がMモードになっている")
        print("- TM1121のBluetoothが有効")
        print("- WindowsのBluetoothがON")
        print("- TM1121をPCの近くに置いている")
        return

    print("")
    print("TM1121発見")
    print(f"Name    : {device.name}")
    print(f"Address : {device.address}")
    print("")
    print("接続しています...")

    try:
        async with BleakClient(
            device,
            timeout=20.0,
        ) as client:
            print("接続成功")
            print(f"Connected: {client.is_connected}")

            await client.start_notify(
                NOTIFY_UUID,
                notification_handler,
            )

            print("")
            print("==============================")
            print("TM1121の測定データを受信中")
            print("Ctrl+Cで終了")
            print("==============================")
            print("")

            while True:
                await asyncio.sleep(1)

    except Exception as e:
        print("")
        print("TM1121との通信中にエラーが発生しました。")
        print(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("")
        print("測定を終了しました。")
```

実行:

```powershell
python record_tm1121.py
```

正常に動作すると、以下のように表示されます。

```text
TM1121を検索しています...
TM1121をService UUIDから発見しました。

TM1121発見
Name    : TM1121
Address : 4C:24:98:4D:03:0E

接続しています...
接続成功
Connected: True

==============================
TM1121の測定データを受信中
Ctrl+Cで終了
==============================

2026-07-25 11:20:01.123  SpO2=98%  Pulse=72 bpm
2026-07-25 11:20:02.124  SpO2=98%  Pulse=73 bpm
2026-07-25 11:20:03.126  SpO2=97%  Pulse=72 bpm
```

---

# 8. CSV出力

同じディレクトリに

```text
tm1121_data.csv
```

が作成されます。

内容:

```csv
timestamp,spo2,pulse,raw_hex
2026-07-25 11:20:01.123,98,72,01 00 62 00 48 00
2026-07-25 11:20:02.124,98,73,01 00 62 00 49 00
2026-07-25 11:20:03.126,97,72,01 00 61 00 48 00
```

`raw_hex` も保存しているため、後からBLEプロトコルを再解析できます。

---

# 9. データフォーマット

実機で確認した結果、Notifyで受信するデータについて

```python
spo2 = data[2]
pulse = data[4]
```

で値を取得できます。

例:

```text
DEC : [1, 0, 98, 0, 72, ...]
```

の場合、

```text
data[2] = 98
→ SpO₂ = 98 %

data[4] = 72
→ Pulse = 72 bpm
```

となります。

ただし、この位置関係については実測によって確認したものであり、
A&D公式通信仕様書との照合を行っていない場合は、
研究・製品利用前に複数条件で値が追従することを確認してください。

---

# 10. トラブルシューティング

## TM1121が見つからない

以下を確認します。

1. TM1121が `M` モードになっている
2. WindowsのBluetoothがON
3. TM1121をPCの近くに置く
4. 他のPCやスマートフォンがTM1121へ接続していない
5. 一度TM1121の電源をOFF/ONする
6. `python scan.py` で再確認する

---

## `Name : None` になる

BLEでは、スキャンのタイミングによってデバイス名が取得できないことがあります。

本READMEの `record_tm1121.py` では名前だけでなく

```text
23444100-9c95-1740-a38a-000bdb712c7c
```

というService UUIDでも検索するため、
`Name : None` でも検出できる場合があります。

---

## 接続できるが値が来ない

以下を確認します。

1. SpO₂センサを指に正しく装着している
2. TM1121本体で測定が開始されている
3. 本体画面にSpO₂と脈拍が表示されている
4. Notify UUIDが以下になっている

```text
23444102-9c95-1740-a38a-000bdb712c7c
```

---

## 値がおかしい

デバッグ時は生データを表示します。

`notification_handler()` 内に以下を追加します。

```python
print("HEX:", data.hex(" "))
print("DEC:", list(data))
```

TM1121本体表示と比較して、

```text
3バイト目 → SpO₂
5バイト目 → 脈拍
```

になっていることを再確認してください。

---

# 11. requirements.txt

環境を再現しやすくするため、以下の `requirements.txt` を作っておくことを推奨します。

```text
bleak
```

インストール:

```powershell
python -m pip install -r requirements.txt
```

さらに厳密な再現性が必要な場合は、動作確認後に

```powershell
python -m pip freeze > requirements.txt
```

を実行し、Bleakのバージョンを固定してください。

---

# 12. 推奨ディレクトリ構成

```text
tm1121_test/
│
├─ .venv/
│
├─ README.md
├─ requirements.txt
├─ scan.py
├─ record_tm1121.py
└─ tm1121_data.csv
```

---

# 13. 最短実行手順

新しいPCで再現する場合は、基本的に以下だけで実行できます。

```powershell
cd tm1121_test

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install bleak

python record_tm1121.py
```

TM1121側は、

```text
Mモード
→ センサ装着
→ 測定開始
→ PCからrecord_tm1121.py実行
```

です。

---

# 14. 確認済みBLE情報

```text
Device
  Name: TM1121

Service
  23444100-9c95-1740-a38a-000bdb712c7c

Characteristics
  23444101-9c95-1740-a38a-000bdb712c7c
    Properties: read, indicate

  23444102-9c95-1740-a38a-000bdb712c7c
    Properties: read, notify

  23444103-9c95-1740-a38a-000bdb712c7c
    Properties: read, write

  23444104-9c95-1740-a38a-000bdb712c7c
    Properties: read, write

  23444105-9c95-1740-a38a-000bdb712c7c
    Properties: read, write

  23444106-9c95-1740-a38a-000bdb712c7c
    Properties: read, write

  23444107-9c95-1740-a38a-000bdb712c7c
    Properties: read, write
```

標準Serviceとして以下も確認済みです。

```text
00001800-0000-1000-8000-00805f9b34fb
Generic Access Profile

00001801-0000-1000-8000-00805f9b34fb
Generic Attribute Profile

0000180a-0000-1000-8000-00805f9b34fb
Device Information
```

---

## 備考

本コードは、TM1121からBLE経由で取得した実データを観察し、

- `data[2]`: SpO₂
- `data[4]`: 脈拍数

と確認した結果に基づいています。

研究用途で長期間利用する場合は、A&Dが提供するTM1121の正式な通信仕様書とも照合し、
データフォーマット、無効値、エラーフラグ、測定状態などを確認することを推奨します。
