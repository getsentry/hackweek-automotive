"""
Sentry CarBuddy - OBD-II Vehicle Diagnostics to Sentry Integration

A headless Raspberry Pi application that reads Diagnostic Trouble Codes (DTCs)
from vehicles via a factory-paired Bluetooth OBD-II adapter and reports them
to Sentry.io for monitoring and alerting.
"""

import obd


def main():
    connection = obd.OBD()
    cmd = obd.commands.SPEED
    response = connection.query(cmd)
    print(response.value)


if __name__ == "__main__":
    main()
