import asyncio
from datetime import datetime

from bleak import BleakClient, BleakScanner


ADDRESS = "4C:24:98:4D:03:0E"

CHAR_INDICATE = "23444101-9c95-1740-a38a-000bdb712c7c"
CHAR_NOTIFY = "23444102-9c95-1740-a38a-000bdb712c7c"


def show_data(label):
    def callback(sender, data: bytearray):
        now = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        print(
            f"{now}  {label}\n"
            f"  HEX : {data.hex(' ')}\n"
            f"  DEC : {list(data)}\n"
            f"  LEN : {len(data)} bytes\n"
        )

    return callback


async def main():
    print("TM1121を検索中...")

    device = await BleakScanner.find_device_by_address(
        ADDRESS,
        timeout=10.0,
    )

    if device is None:
        print("TM1121が見つかりません。")
        return

    print("TM1121発見")
    print("接続中...")

    async with BleakClient(device, timeout=20.0) as client:
        print("接続成功！")

        # 現在値も一度読んでみる
        for uuid, name in [
            (CHAR_INDICATE, "CHAR01"),
            (CHAR_NOTIFY, "CHAR02"),
        ]:
            try:
                value = await client.read_gatt_char(uuid)
                print(
                    f"{name} initial value:\n"
                    f"  HEX : {value.hex(' ')}\n"
                    f"  DEC : {list(value)}\n"
                )
            except Exception as e:
                print(f"{name} read error: {e}")

        print("CHAR01(indicate)を購読...")
        await client.start_notify(
            CHAR_INDICATE,
            show_data("CHAR01"),
        )

        print("CHAR02(notify)を購読...")
        await client.start_notify(
            CHAR_NOTIFY,
            show_data("CHAR02"),
        )

        print("\n================================")
        print("受信待機中")
        print("TM1121で測定を開始してください。")
        print("Ctrl+C で終了します。")
        print("================================\n")

        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n終了しました。")