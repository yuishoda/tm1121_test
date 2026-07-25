import asyncio
from bleak import BleakClient, BleakScanner

ADDRESS = "4C:24:98:4D:03:0E"


async def main():
    print("TM1121を検索しています...")

    device = await BleakScanner.find_device_by_address(
        ADDRESS,
        timeout=10.0,
    )

    if device is None:
        print("TM1121が見つかりません。")
        print("TM1121をMモードでONにしてください。")
        return

    print("\nTM1121発見")
    print(f"Name    : {device.name}")
    print(f"Address : {device.address}")

    print("\n接続中...")

    try:
        async with BleakClient(device, timeout=20.0) as client:

            print("\n==========================")
            print("TM1121 接続成功！")
            print("==========================")
            print(f"Connected: {client.is_connected}")

            print("\n===== GATT SERVICES =====")

            for service in client.services:

                print("\n----------------------------------")
                print(f"SERVICE")
                print(f"UUID : {service.uuid}")
                print(f"Name : {service.description}")

                for char in service.characteristics:

                    print("\n  CHARACTERISTIC")
                    print(f"  UUID       : {char.uuid}")
                    print(f"  Properties : {char.properties}")

                    for descriptor in char.descriptors:
                        print(
                            f"    Descriptor : {descriptor.uuid}"
                        )

    except Exception as e:
        print("\n接続エラー")
        print(type(e).__name__, e)


if __name__ == "__main__":
    asyncio.run(main())