import asyncio
from bleak import BleakScanner


async def scan():
    devices = await BleakScanner.discover(
        timeout=10,
        return_adv=True,
    )

    return {
        address: (device, adv)
        for address, (device, adv) in devices.items()
    }


async def main():
    print("======================================")
    print("TM1121をOFFにしてください")
    input("準備できたらEnterを押してください > ")

    print("\nOFF状態をスキャン中...")
    off_devices = await scan()

    print(f"{len(off_devices)} 台見つかりました")

    print("\n======================================")
    print("TM1121をMモードでONにしてください")
    print("指を装着して測定状態にしてください")
    input("準備できたらEnterを押してください > ")

    print("\nON状態をスキャン中...")
    on_devices = await scan()

    print("\n======================================")
    print("OFF時には無く、ON時に現れたデバイス")
    print("======================================")

    found = False

    for address, (device, adv) in on_devices.items():

        if address not in off_devices:
            found = True

            print("\n------------------------------")
            print(f"Name     : {device.name}")
            print(f"Address  : {device.address}")
            print(f"RSSI     : {adv.rssi}")
            print(f"Local    : {adv.local_name}")
            print(f"Services : {adv.service_uuids}")
            print(
                f"Manufacturer data : "
                f"{adv.manufacturer_data}"
            )

    if not found:
        print("\n新しく出現したBLEデバイスはありませんでした。")


if __name__ == "__main__":
    asyncio.run(main())