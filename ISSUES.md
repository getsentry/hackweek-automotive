- The systemd `obd-connect.service` errors with "resource is busy". Workaround is to
  manually connect via `sudo rfcomm connect hci0 <address>`.
- Until the car is started, `obd.status()` is in "OBD connected", which means not
  connected to ECU. The application should try to reconnect or refresh the connection
  until it works.
- Check if we can put the car into diagnostic mode via an OBD command.
- Engine off stops diagnostic mode and crashes app. The app should start polling again.
