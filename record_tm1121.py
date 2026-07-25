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
