import asyncio

from bleak import BleakScanner


async def main():
    print("BLEデバイスを10秒間スキャンします...\n")

    devices = await BleakScanner.discover(
        timeout=10.0,
        return_adv=True,
    )

    for address, (device, adv) in devices.items():
        print("=" * 60)
        print(f"Name    : {device.name}")
        print(f"Address : {device.address}")
        print(f"RSSI    : {adv.rssi}")
        print(f"Local   : {adv.local_name}")
        print(f"Services: {adv.service_uuids}")


if __name__ == "__main__":
    asyncio.run(main())