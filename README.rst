.. meta::
   :description: Create A Raspberry Pi 3 Model B and u-blox CAM-M8C GPS NTP server.
   :keywords: GPS, NTP, Raspberry Pi, I2C, NTPsec
   :locale: en_US
   :author: Michael Johnson
   :robots: index

.. |I2C| replace:: I\ :sup:`2`\ C


=================================================================
Create A Raspberry Pi 3 Model B and u-blox CAM-M8C GPS NTP server
=================================================================

.. contents::
   :depth: 2

Introduction
************

This is a project to create a Network Time Protocol (NTP) server using a
Raspberry Pi 3 Model B and a u-blox CAM-M8C GNSS module.

Yes, there are a lot of existing web pages describing how to setup a Raspberry
PI to be a GPS based NTP server, but none of them had the level of detail I
wanted.

* GPS time pulse output for Pulse Per Second (PPS) synchronization.
* A full Linux server OS to support additional services on the Raspberry Pi.
* U-blox based chipset (I have used them for projects at a previous employer).
* Multiple independent interfaces for the GPS chip so it can be used for
  multiple purposes.
* Reasonable cost as this is a hobby project.

I should note that a Raspberry Pi can be used as an NTP server without GPS
integration by simply synchronizing to NTP server pools available on the
internet. However, this project was to setup GNSS synchronized stratum 1 NTP
server.

I started out using `gpsd <https://gpsd.gitlab.io/gpsd/index.html>`_ and
`chrony <https://chrony.tuxfamily.org/>`_ for the NTP service, but found both
to be fairly opinionated and added unnecessary layers to the software stack
which added latency. It was a useful learning experience, but I ended up
removing those packages and installing NTPsec instead. Both gpsd and chrony
are useful for simple deployments and for intermittently connected clients, but
they did not let me control the u-blox module the way I want to.

Chrony does have one advantage, which is kernel or hardware timestamping when
synchronizing over the network. However, the Raspberry Pi 3 network interface
does not support hardware timestamping. I plan to setup linuxptp to provide
Precision Time Protocol (PTP) on my network in the future. This will leverage
the timestamping features of the kernel and/or network interface. I expect this
will require a Raspberry Pi 4, possibly with a USB network interface that
supports hardware timestamping. See the `Future Work`_ section for more
information.

Hardware
********

I selected parts that I already had available or were familiar with. As
mentioned in the introduction, I have used u-blox modules before and have been
impressed with their capabilities. I also already had a Raspberry Pi 3-B
hosting my other network services.

* `Raspberry Pi 3 model B <https://www.raspberrypi.org/products/raspberry-pi-3-model-b/>`_
* `CanaKit setup for the Raspberry Pi 3 <https://www.canakit.com/raspberry-pi/raspberry-pi-3-kits>`_ (Note: Some of these kits include the Raspberry Pi 3 model
  B board)

  * Heatsinks
  * Power supply
  * Case

* 128GB "high endurance" microSD card
* `OzzMaker BerryGPS-IMUv3 <http://ozzmaker.com/berrygps-berrygps-imu-quick-start-guide/>`_ (contains the `u-blox CAM-M8C module <https://www.u-blox.com/en/product/cam-m8-series>`_)
* Active GPS antenna with the required uFL to SMA adapter

In addition, I already had the required USB keyboard, USB mouse, HDMI,
microSD to USB adapter, and network cables required to set this up.

I have created an Amazon "Idea List" with the
`list of parts here <http://a.co/2Z7dNhq>`_. (Note: I do not get any
compensation if you order from this list, it's just there for your convenience)

You may be able to source these parts cheaper or substitute alternate parts.

I selected the OzzMaker BerryGPS-IMUv3 over the other GPS offerings for a few
reasons:

* It uses a modern u-blox module.
* It pulls the UART, |I2C|, and PPS pins out from the u-blox module.
* Supports an external antenna.

In the end, the BerryGPS-IMUv3 has more capability in the IMU than I need and
is a bit more expensive than some options, but I am happy with the board and
the responsiveness I got from OzzMaker when I had a question about the board.

.. note::

    The BerryGPS-IMUv3 does require some solder work for this project.
    The 5x2 header for the Raspberry Pi needs to be soldered to the
    BerryGPS-IMUv3 board. You will also need to solder a wire from the PPS pin
    hole on the BerryGPS-IMUv3 board to one of the GPIO pins on the
    Raspberry PI. In addition, if you want access to the |I2C|
    interface on the u-blox module, you will need to solder wires to extend
    the |I2C| bus.

I am recommending a "high endurance" microSD purely due to the write load
running Linux can have. Specifically, the logging and other actions under /var.
Unfortunately, most microSD cards have very low write endurance and most
do not provide information on the endurance of a device or if the device
includes write wear leveling. Purchasing a microSD card that is larger than
you need may help extend the life of the card if write wear leveling is in use.
Below I will make some recommendations about ways to reduce the write load
for this use case.

Soldering
*********

1. Solder the 5x2 header onto the BerryGPS-IMUv3 board. The header should be
   on the back of the board so that it will join with the Raspberry Pi 40 pin
   header.
2. Solder a wire from the "T_PULSE" pin hole on the BerryGPS-IMUv3 to a free
   GPIO ping on the Raspberry Pi. I selected the GPIO 21 pin. You can use a
   jumper cable with a female connector for the GPIO pin if you have one, but
   make sure it is a tight fit with the pin. Make note of the pin you selected
   as you will need it later during the kernel configuration step.
3. Optionally, connect the u-blox module |I2C| bus to the
   BerryGPS-IMUv3 |I2C| bus.

   * Solder a wire from the SDA pin hole to the uSDA pin hole.
   * Solder a wire from the SCL ping hole to the uSCL pin hole.

Booting the Raspberry Pi
************************

I chose to use Ubuntu Server on my Raspberry Pi for this project. It is a
complete Linux distribution that includes all of the packages I needed for this
project but also the other services I want to run on the Raspberry Pi. They
also regularly release patches and updates which is nice.

At the time of this writing, version 19.10.1 (Eoan Ermine) of Ubuntu Server was
available. I plan to upgrade this device to 20.04 LTS (Focal Fossa) when it is
released.

1. Download the 64-bit version of Ubuntu Server for the Raspberry Pi 3 from
   the `Ubuntu Raspberry Pi page <https://ubuntu.com/download/raspberry-pi>`_.
2. Follow the instructions on this page to flash the microSD card with the
   downloaded image.

   .. note::

      If you use the Win32Diskimager tool, it will not run if you have any RAM
      disks mounted in Windows. This is listed in the release notes, but you
      have to look to find it. I use a RAM disk as a temporary cache and got
      blocked by this issue for a bit. Simply unmounting the RAM disk allows
      the application to start.

3. Make sure the BerryGPS-IMUv3 is not yet attached to the Raspberry Pi. The
   NEMA codes from the GPS module UART will halt the Raspberry Pi from booting.
4. Install the microSD card in the Raspberry Pi and power it up.
5. You will see the normal Linux kernel boot sequence on the screen. On first
   boot, give it some time before attempting to login. The cloud-init on the
   first run will take some time even after the login prompt is up. The default
   image username and password of "ubuntu" will not work until cloud-init is
   finished. Once you see the kernel booting, it is a good time to get a
   beverage.
6. Once you are logged in, do your updates:

   .. code-block:: bash

      sudo apt-get update
      sudo apt-get dist-upgrade

7. You will also need some additional packages:

   .. code-block:: bash

      sudo apt-get install pps-tools rng-tools ntpsec cpufrequtils dkms python3

8. Configure the kernel command line:

   * Edit the /boot/firmware/nobtcmd.txt

     * Remove the "console=ttyAMA0,115200" section. This stops the kernel from
       using the Raspberry Pi UART as a serial console. We will be using it for
       the u-blox UART.
     * Add "nohz=off" to the command line. This causes the kernel to never omit
       scheduling clock ticks.

.. _kernel device tree:

9. Configure the kernel device tree:

   * Edit the /boot/firmware/syscfg.txt

     * Add "dtparam=i2c_arm=off". This disables the broken |I2C| bus
       on the Broadcom chip used in the Raspberry Pi 3 model B. The hardware
       |I2C| bus on the Broadcom chip does not support clock
       stretching used by the u-blox module.
     * Add "dtparam=spi=off". This disables the SPI bus on the Raspberry Pi.
       We don't need it.
     * Add "dtoverlay=pps-gpio,gpiopin=21". This sets the GPIO pin on the
       Raspberry Pi that is connected to the "T_PULSE" or PPS pin hole on the
       BerryGPS-IMUv3. If you used a GPIO pin other than 21 in the soldering
       section above, replace the "21" on this line with the correct pin
       number.
     * Add "dtoverlay=pi3-disable-bt". This disables the Bluetooth device on
       the Raspberry Pi. This is optional, but I don't need it so I am going to
       disable it.
     * Add "dtoverlay=pi3-disable-wifi". This disables the WiFi device on the
       Raspberry Pi. This is optional, but I don't need it so I am going to
       disable it.
     * Add "dtoverlay=i2c-gpio,bus=3,i2c_gpio_sda=02,i2c_gpio_scl=03,i2c_gpio_delay_us=2". This enables the software |I2C| driver using GPIO pins on
       the Raspberry Pi. This approach avoids the corruption that occurs with
       the hardware Raspberry Pi |I2C| bus due to clock stretching.
       This is optional and only required if you intend to use the
       |I2C| bus on the BerryGPS-IMUv3.

10. Enable the pps-gpio kernel module at boot:

    .. code-block:: bash

       echo "pps-gpio" | sudo tee -a /etc/modules-load.d/pps-gpio.conf

11. Shutdown getty on the ttyAMA0 device:

    .. code-block:: bash

       sudo systemctl stop serial-getty@ttyAMA0.service
       sudo systemctl disable serial-getty@ttyAMA0.service

12. Setup udev to disable echo on the ttyAMA0 device:

    .. code-block:: bash

       sudo cp udev/09.ttyAMA0.rules /etc/udev/rules.d

    If you do not disable echo on the tty device, you will see garbage in your
    NMEA message stream from the ttyAMA0 device and GNTXT NMEA messages with
    "More than 100 frame errors, UART RX was disabled" in them.

13. Set the CPU frequency governor to "performance":

    .. code-block:: bash

       echo 'GOVERNOR="performance"' | sudo tee -a /etc/default/cpufrequtils

14. Reboot and disable the uboot boot delay to stop the GPS messages from
    aborting the boot process.

    * Run "sudo reboot"
    * When you see text, after the Raspberry Pi color gradient, start hitting
      the "enter" key until you get a uboot prompt.
    * Enter "setenv bootdelay -2". This disables the uboot delay so that NMEA
      messages from the u-blox UART do not interrupt the boot sequence.
    * Enter "saveenv". This saves the above setting so it is in effect on each
      boot.

15. Attach the BerryGPS-IMUv3 board to the Raspberry Pi:

    * Power off the Raspberry Pi.
    * Install the plastic support pins included with the BerryGPS-IMUv3. Only
      two line up for me.
    * Attach the BerryGPS-IMUv3 to the Raspberry Pi by lining up the 5x2 header
      with the top GPIO pins (1 and 2) on the Raspberry Pi 3.
    * Attach the antenna to the BerryGPS-IMUv3.
    * Be sure to set the antenna switch to "EXT" to use the external antenna.
    * Attach the PPS (T_PULSE) wire to the GPIO pin (21 in my case) if you have
      not already done so.

Test the BerryGPS-IMUv3 Integration
***********************************

1. Power up the Raspberry Pi. It should boot back to the login prompt if the
   previous steps were completed correctly.
2. Login and run a test on the PPS source (ctrl-c to exit):

   .. code-block:: bash

      sudo ppstest /dev/pps0

   This should show similar output to this example:

   .. code-block::

      trying PPS source "/dev/pps0"
      found PPS source "/dev/pps0"
      ok, found 1 source(s), now start fetching data...
      source 0 - assert 1578164816.999990228, sequence: 966890 - clear  0.000000000, sequence: 0
      source 0 - assert 1578164817.999992699, sequence: 966891 - clear  0.000000000, sequence: 0

3. Check that the NMEA messages are streaming on the ttyAMA0 device
   (ctrl-c to exit):

   .. code-block:: bash

      sudo cat /dev/ttyAMA0

   This should show similar output to this example:

   .. code-block::

      $GNRMC,193854.00,V,0000.00000,N,00000.00000,W,0.015,,040120,,,A*71

      $GNZDA,193855.00,04,01,2020,00,00*7E

   You should not see any non-ascii characters in this stream.
   Note: I have zeroed out the coordinates and marked the message as 'V',
   invalid, here for privacy reasons. Your RMC message will likely have an
   'A' and actual coordinates.

4. If these steps all check out ok, you have successfully completed the above
   steps and can now move on to configuring the NTP service on your Raspberry
   Pi.

5. If not, go back through the initial steps and make sure you didn't miss a
   step. Also, double check you solder work. Adafruit has an excellent
   `Common Soldering Problems <https://learn.adafruit.com/adafruit-guide-excellent-soldering/common-problems>`_ guide that may help.

Configuring NTPsec
******************

1. Allow the ntpd process access to the devices:

   .. code-block:: bash

      echo '@{NTPD_DEVICE}="/dev/ttyAMA0" "/dev/pps0"' | sudo tee -a /etc/apparmor.d/tunables/ntpd
      sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.ntpd

2. Configure ntpsec:

   * Create the /etc/ntpsec/ntp.d/refclock.conf file.

     * Add "refclock nmea flag1 1 path /dev/ttyAMA0 ppspath /dev/pps0 baud
       9600". This enables the NMEA driver with a PPS source.

   .. note::

      You may want to add "flag4 1" to this string if your NTP service will
      be accessible from untrusted systems. This will mask the GPS antenna
      location information from being avialable in the logs or via
      "ntpq -c clockvar <server>".

3. Optionally update the network NTP pool configuration:

   * Edit the /etc/ntpsec/ntp.conf file.

     * Modify the "pool" configuration lines to reflect network NTP pool
       you would like to use. By default, Ubuntu configures these for
       "ubuntu.pool.ntp.org" pools. See the
       `NTP Pool Project <https://www.ntppool.org/en/>`_
       for more information about available pools.

   .. note::

      If you don't define any additional time sources, ntpsec will not select
      the PPS source and set the system clock. This is because the default
      configuration file includes a "tos" "minsane" configuration that requires
      multiple servers. You can comment out this line if you will only be using
      the NMEA and PPS source from the CAM-M8C module.

4. Restart the ntp service to load the new configuration:

   .. code-block:: bash

      sudo systemctl restart ntpsec

5. Check the NTP server peer status:

   .. code-block:: bash

      sudo ntpq -np

   You should see output similar to this:

   .. code-block::

      remote           refid           st t when poll reach   delay   offset   jitter
      ===============================================================================
      oNMEA(0)         .GPS.            0 l   37   64  377   0.0000   0.0129   0.0014

   It will take a few minutes before the 'o' appears in front of the NMEA word.
   This 'o' means that the NTP service is receiving NMEA messages and has
   synced to the PPS time pulses from the kernel.

Graphing with ntpviz (Optional)
*******************************

The NTPsec package we are using for the NTP service on Linux has an optional
package called ntpsec-ntpviz. ntpviz reads the statistics files produced by
ntpsec and generates HTML pages with graphs of the ntp service performance.

To use ntpviz, you will need to install a few more packages:

   .. code-block:: bash

      sudo apt-get install gnuplot-nox ntpsec-ntpviz

   .. note::
      I used gnuplot-nox here because if you don't specify this, installing the
      ntpsec-ntpviz package will pull in the X windows versions of gnuplot,
      which installs the full X windows environment on the Raspberry Pi.

The ntpsec-ntpviz package will automatically configure ntpsec to write out
the required statistics files and will enable cron jobs to generate the HTML
pages. The default configuration will produce daily and weekly summaries.
This package will also enable the /ntpviz path in Apache if it is installed.

The ntpsec package includes a cron job that will automatically rotate the stats
files.

Reducing Flash Device Wear (Optional)
-------------------------------------

Flash storage devices have a limited number of program/erase (P/E), or write,
cycles they can tolerate before wearing out. This is especially true of microSD
cards. Unfortunately, most microSD manufactures do not provide a specification
for the number of P/E cycles their device is expected to handle.

Some flash devices use write wear leveling to increase the overall life of a
flash device by using extra un-used space on the device to write new data
before resorting to re-writing. Unfortunately, like the expected P/E cycles,
most flash vendors do not disclose if their device has wear leveling
capabilities.

Due to this limitation of flash storage, and the lack of good data about the
endurance of the microSD card, I have recommended getting an oversized "high
endurance" microSD card.

Beyond that, we can take some steps to reduce the amount of wear we put on
the microSD card in our Raspberry Pi.

Linux based systems need to write data to storage on a regular basis. This
includes everything from logs, socket files, process ID files, and other
configuration data. Most of these writes occur under the /var file path, with
the highest write files typically writing to files under /var/log.

Normal logging does not produce a lot of regular writes, but the ntpviz package
we installed above does. Reducing the Linux filesystem write wear is beyond the
scope of this document, but I will provide some ideas to reduce the wear from
ntpviz.

The ntpsec-ntpviz package enables the following statistics logging: loopstats,
peerstats, and clockstats.
Each of these can write hundreds of thousands of lines a data per day and will
later be re-written to disk in compressed form. Finally, they will be expired
out and deleted after a week. On top of this, ntpviz will rewrite the graphs
and HTML content every hour.

Since this data is purely for monitoring, and does not impact the performance
of the ntp service, I would recommend storing these in RAM instead of on
the microSD flash. This means they will not persist across reboots, but they
will also not increase the wear on the flash storage. After each reboot, the
graphs will start over as if you just installed ntpsec-ntpviz.

To store these files in RAM, we need to setup these paths on tmpfs:

* Configure the fstab to mount the directories on tmpfs:

  .. code-block:: bash

     echo "tmpfs   /var/log/ntpsec tmpfs   rw,size=5M,nodev,nosuid,noexec,uid=ntpsec,gid=ntpsec,mode=755 0 0" | sudo tee -a /etc/fstab
     echo "tmpfs   /var/lib/ntpsec/ntpviz  tmpfs   rw,size=10M,nodev,nosuid,noexec,uid=root,gid=root,mode=755 0 0" | sudo tee -a /etc/fstab

* Reboot to make sure all of the ntpviz processes are using the new filesystem:

  .. code-block:: bash

     sudo reboot

Optionally, you can clear out the already stored data in these directories
before the reboot. Even if you do not, the old data will not be used.

BerryGPS-IMUv3 Temperature Graphing (Optional)
----------------------------------------------

By default, ntpviz will graph the temperature reading from the Raspberry Pi
processor as "ZONE0" using the "ntplogtemp" program. ntplogtemp has built in
support for pulling temperature readings from alternate sources, one of which
is using a command called "temper-poll".

The BerryGPS-IMUv3 includes a temperature sensor that is attached to the
|I2C| bus and I have created a python script that is compatible with
the ntplogtemp use of "temper-poll" that can be used to capture the temperature
from the BerryGPS-IMUv3 called "get-imu-temp.py". This can be installed and
symbolic linked to the name "temper-poll" and ntplogtemp will automatically
start using it to collect the "TEMPER0" temperature reading from the
BerryGPS-IMUv3. I have found this temperature reading to be much closer to the
ambient temperature than the reading from the Raspberry Pi CPU.

To enable the BerryGPS-IMUv3 temperature reading:

1. Install the required python module:

   .. code-block:: bash

      sudo apt-get install python3-smbus

2. Copy the get-imu-temp.py application into /usr/local/bin:

   .. code-block:: bash

      sudo cp -p get-imu-temp/get-imu-temp.py /usr/local/bin

3. Link the "temper-poll" name to get-imu-temp.py:

   .. code-block:: bash

      sudo ln -s /usr/local/bin/get-imu-temp.py /usr/local/bin/temper-poll

.. note::

   The get-imu-temp.py code expects the BerryGPS-IMUv3 |I2C| device to
   be on |I2C| bus 3. This is how I configured the |I2C| bus
   above in the `kernel device tree`_ section.

After the next ntpviz daily graph run, you should see the "TEMPER0" label
appear on the "Local Frequency/Temp" daily graph produced by ntpviz. By
default, this runs once an hour.

You can also verify the "TEMPER0" temperature polling by looking at the
/var/log/ntpsec/temps file. After about five minutes, you should see a
temperature reading for "TERMER0" in addition to the "ZONE0" readings.

By default, all temperature values are in centigrade.

.. note::

   Using a case around your Raspberry Pi and BerryGPS-IMUv3 may improve your
   temperature stability, which in turn may improve the stability of the
   crystal oscillator in the u-blox CAM-M8C GNSS module as the CAM-M8C module
   does not include a temperature compensated crystal oscillator.
   However, this will put more thermal stress on the components and, if the
   Raspberry Pi is under heavy load, the Raspberry Pi may throttle the CPU.
   See the `Raspberry Pi frequency management and thermal control <https://www.raspberrypi.org/documentation/hardware/raspberrypi/frequency-management.md>`_
   for more information on thermal throttling.

Configuring the u-blox Module (Optional)
****************************************

In general, the u-blox GNSS chips are highly configurable. This includes
settings that can enhance the stability of your NTP service.

Connecting u-center to the Raspberry Pi
---------------------------------------

One of the nice things about u-blox is that they provide a graphical tool that
allows you to see how your u-blox module is performing and configure it. This
software is called u-center. You can download `u-center from the u-blox website <https://www.u-blox.com/en/product/u-center>`_ for free.

The u-blox u-center software supports connecting to the u-blox module over a
network.

To connect u-center to the Raspberry Pi, you will need to install the ser2net
package and make sure it doesn't automatically start on boot:

.. code-block:: bash

   sudo apt-get install ser2net
   sudo systemctl disable ser2net

Configure ser2net for u-center connection:

.. code-block:: bash

   echo "6000:raw:600:/dev/ttyAMA0:9600 NONE 1STOPBIT 8DATABITS XONXOFF LOCAL -RTSCTS" | sudo tee -a /etc/ser2net.conf

If you have configured NTPsec to use the |I2C| interface, you do not
need to stop the NTP service to use u-center. However, if you are not using the
|I2C| interface for NTPsec, you will need to stop NTPsec before
starting the ser2net service:

.. code-block:: bash

   sudo systemctl stop ntpsec

Now that you have ser2net prepared you can start the ser2net service:

.. code-block:: bash

   sudo systemctl start ser2net

Connect the u-center application to the Raspberry Pi:

* From the top menu, select **Receiver**.
* Select **Connection** from the **Receiver** menu.
* Select **Network Connection** from the **Connection** menu.
* Select **New** from the **Network Connection** menu.
* In the **Address** field, enter the URL to the Raspberry Pi:

  .. code-block::

     tcp://<ip address>:6000

* In the ser2net configuration we used port 6000, so I have indicated that in
  this above example.

At this point you should see satellites populating in the satellite level
history window.

Once you are done using u-center, be sure to shut down ser2net as it does not
have any access control.

.. code-block:: bash

   sudo systemctl stop ser2net

Configuring the u-blox CAM-M8C Module
-------------------------------------

If you cannot run the u-center software, you can still build a custom
configuration using the `u-blox protocol specification <https://www.u-blox.com/en/docs/UBX-13003221>`_ document.

To configure the u-blox module:

* Select the **View** menu.
* From the **View** menu, select **Configuration View**.

This will open the Configure window. It will show you the current configuration
values on the CAM-M8C module. At the bottom of the window, there is a Poll
button that allows you to query the module to load the current configuration.

Along the left side of the window is the list of possible configuration
categories. Not all of these categories apply to the CAM-M8C module.

On the right side of the window are the configuration settings in the selected
category. If you make a change to one of these settings, you must click the
Send button at the bottom of the window for the configuration settings to be
applied to the module.

.. note::

   The u-blox CAM-M8C module does not have persistent storage for the
   configuration. The configuration must be re-applied at power up.

   I will explain how to set this up in the
   `Applying u-blox Configuration Settings on Boot`_ section.

Configuration Settings to Consider
----------------------------------

In this section I will go over the u-center configuration categories and make
recommendations on settings that may improve the timing stability.

GNSS (GNSS Config)
~~~~~~~~~~~~~~~~~~

This section allows the configuration of the Global Navigation Satellite System
(GNSS) the module will track and use for time synchronization.

* Confirm that GPS is enabled, with a minimum of 8 and maximum of 16.
* Disable the SBAS. This is recommended in the `u-blox protocol specification <https://www.u-blox.com/en/docs/UBX-13003221>`_ document, Time Pulse section
  19.2.
* Enable Galileo with a minimum of 4 and maximum of 8.
* Confirm QZSS is enabled, with a minimum of 0 and maximum of 3. This is recommended in the `u-blox protocol specification <https://www.u-blox.com/en/docs/UBX-13003221>`_ document, GNSS system configuration section 32.10.9.1.
* Confirm GLONAAS is enabled, with a minimum of 8 and a maximum of 14.
* All other GNSS systems should be disabled.
* Click the **Send** button at the bottom.

.. note::

   Galileo satellites will not appear in u-center until we enabled NMEA version
   4.1 messages in the NMEA (NMEA Protocol) section below.

   GLONASS satellites will be visible, but will not lock in and be used for up
   to thirty minutes because the GLONASS satellites only transmit the ephemeris
   information every thirty minutes.

   Changing the GNSS settings requires a cold start of the GNSS subsystem as
   noted in the `u-blox protocol specification
   <https://www.u-blox.com/en/docs/UBX-13003221>`_ section 4.2.1. I will
   discuss how to do this in the `Applying u-blox Configuration Settings on
   Boot`_ section below.

MSG (Messages)
~~~~~~~~~~~~~~

This section configures which messages the u-blox module will send out which
communications port. The NTPsec NMEA driver only requires one of the following
messages to synchronize the time: $GPRMC, $GPGLL, $GPGGA, or $GPZDA. The
default settings for the u-blox module send many additional messages used for
navigation.

We can reduce the latency of the required messages and reduce the processing
power that NTPsec will use by limiting the messages sent from the u-blox
device. This is optional configuration as NTPsec can successfully operate with
the default message settings.

.. note::

   As you are configuring the messages you will see that the other u-blox
   module interfaces are listed and may be enabled. This is ok. We will disable
   the unused interfaces in the `PRT (Ports)`_ section.

* If you are only using the UART interface (ttyAMA0) and want status and
  navigation messages in addition to the timing messages:

  * Leave the Messages defaults.

* If you are only using the UART interface (ttyAMA0) and are only using the
  u-blox module for NTPsec:

  1. Select "F0-00 NMEA GxGGA" from the drop down, uncheck "UART1" On box,
     click the **Send** button at the bottom.
  2. Select "F0-01 NMEA GxGLL" from the drop down, uncheck "UART1" On box,
     click the **Send** button at the bottom.
  3. Select "F0-02 NMEA GxGSA" from the drop down, uncheck "UART1" On box,
     click the **Send** button at the bottom.
  4. Select "F0-03 NMEA GxGSV" from the drop down, uncheck "UART1" On box,
     click the **Send** button at the bottom.
  5. Select "F0-05 NMEA GxVTG" from the drop down, uncheck "UART1" On box,
     click the **Send** button at the bottom.
  6. Select "F0-05 NMEA GxZDA" from the drop down, **check** "UART1" On box,
     click the **Send** button at the bottom.

  At this point you should only see $GNRMC and $GNZDA messages being output
  over the UART (ttyAMA0) device.

* If you have enabled the |I2C| device (ttyUBLX0) and would like to
  use the |I2C| device for NTPsec (Please see the |I2C| Warning_):

  1. Leave all of the "UART1" settings using the defaults.
  2. Select "F0-00 NMEA GxGGA" from the drop down, uncheck "I2C" On box,
     click the **Send** button at the bottom.
  3. Select "F0-01 NMEA GxGLL" from the drop down, uncheck "I2C" On box,
     click the **Send** button at the bottom.
  4. Select "F0-02 NMEA GxGSA" from the drop down, uncheck "I2C" On box,
     click the **Send** button at the bottom.
  5. Select "F0-03 NMEA GxGSV" from the drop down, uncheck "I2C" On box,
     click the **Send** button at the bottom.
  6. Select "F0-05 NMEA GxVTG" from the drop down, uncheck "I2C" On box,
     click the **Send** button at the bottom.
  7. Select "F0-05 NMEA GxZDA" from the drop down, **check** "I2C" On box,
     click the **Send** button at the bottom.

  At this point you should only see $GNRMC and $GNZDA messages being output
  over the |I2C| device (ttyUBLX0) and multiple message types over
  the UART (ttyAMA0) device.

NAV5 (Navigation 5)
~~~~~~~~~~~~~~~~~~~

This section configures how the u-blox module navigation engine interprets the
measurements.

* From the "Dynamic Model" drop down, select the "2 - Stationary" setting.
* Click the **Send** button at the bottom.

This is the recommended setting for timing applications in the 
`u-blox protocol specification <https://www.u-blox.com/en/docs/UBX-13003221>`_
document section 8.1.

NMEA (NMEA Protocol)
~~~~~~~~~~~~~~~~~~~~

This section configures the NMEA protocol output from the u-blox module.

* From the "NMEA Version" drop down, select "4.1".
* Click the **Send** button at the bottom.

This will enable the output of the Galileo satellites.

PRT (Ports)
~~~~~~~~~~~

This section configures the u-blox module output interfaces.

* If you are only using the UART interface (ttyAMA0):

  1. Select "0 - I2C' from the "Target" drop down.
  2. Select "none" in the "Protocol in" drop down.
  3. Select "none" in the "Protocol out" drop down.
  4. Click the **Send** button at the bottom.
  5. Select "3 - USB' from the "Target" drop down.
  6. Select "none" in the "Protocol in" drop down.
  7. Select "none" in the "Protocol out" drop down.
  8. Click the **Send** button at the bottom.

  This will disable the |I2C| and USB interfaces on the u-blox module,
  leaving just the UART1 interface enabled.

* If you are using both the UART (ttyAMA0) and the |I2C| (ttyUBLX0)
  interfaces:

  1. Select "0 - I2C' from the "Target" drop down.
  2. Select "none" in the "Protocol in" drop down.
  3. Select "1 - NMEA" in the "Protocol out" drop down.
  4. Click the **Send** button at the bottom.
  5. Select "3 - USB' from the "Target" drop down.
  6. Select "none" in the "Protocol in" drop down.
  7. Select "none" in the "Protocol out" drop down.
  8. Click the **Send** button at the bottom.

  This will configure the |I2C| interface to only output NMEA messages
  and will disable the USB interface. It will also leave the default setting
  for the UART1 interface to support UBX and NMEA messages.

.. note::

   This section also configures the baud rate of the UART1 interface. We will
   discuss changing the UART1 baud rate later in this section.

   The speed of the |I2C| interface is defined by the Linux device
   tree parameters. The default values provide more than enough bandwidth
   for the NMEA RMC and ZDA messages.

TP (Timepulse)
~~~~~~~~~~~~~~

This section configures the time pulse output on the Pulse Per Second (PPS)
pin.

The only setting we need to configure here is the cable delay.

The formula to calculate the cable delay is:

.. math::

   D = \frac{L \cdot C}{V}

:D: Cable delay in nanoseconds
:L: Cable length in feet
:C: Constant derived from velocity of light: 1.016
:V: Nominal velocity of propagation expressed as decimal, i.e. %66 = 0.66

You can find the nominal velocity of propagation from the cable datasheet
provided by the manufacturer.

For example, my cable is RG316 which has a nominal velocity of propagation of
69.5.

The cable delay for my antenna is 15.16637681 ns.

* To configure your antenna cable delay:

  1. Calculate the cable delay in nanoseconds.
  2. Enter this value in the "Cable Delay" box. Using my value, I enter "15".
  3. Click the **Send** button at the bottom.

Applying u-blox Configuration Settings on Boot
----------------------------------------------

Once you have configured the module, you can save this configuration to a file
that can be used to configure the module on boot.

Saving the configuration from u-center
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To save the configuration from u-center:

* From the top menu, select **Tools**.
* On the **Tools** menu, select **Receiver Configuration**.
* In the **Load/Save Receiver Configuration** window, specify your configuration
  file save location in the **Configuration File** field.
* Click the **Transfer GNSS -> File** button to start the configuration save
  process.

.. note::
  
   There may be error messages while saving some configuration categories. This
   is ok. The failed categories do not apply to this u-blox module.

Using the u-blox-cfg-loader.py Tool
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

I have included a simple python3 application that will load a u-center saved
configuration file into a u-blox module called u-blox-cfg-loader.py. We can use
this to configure the u-blox module when the Raspberry Pi boots.

* Copy the u-blox-cfg-loader.py into /usr/local/bin on your Raspberry Pi.

  .. code-block:: bash

     sudo cp -p u-blox-cfg-loader.py /usr/local/bin

* Copy your u-center configuration file into /etc on your Raspberry Pi:

  .. code-block:: bash

     sudo cp u-blox.cfg /etc/u-blox.cfg
     sudo chmod 644 /etc/u-blox.cfg
     sudo chown root.root /etc/u-blox.cfg 

* Configure udev to run the u-blox-cfg-loader.py on boot:

  .. code-block:: bash

     sudo cp udev/10.u-blox-cfg-loader.rules /etc/udev/rules.d

* Run the u-blox-cfg-loader.py tool to load your configuration without
  requiring a reboot:

  .. code-block:: bash

     sudo /usr/local/bin/u-blox-cfg-loader.py --port /dev/ttyAMA0 --file /etc/u-blox.cfg

On future reboots of the Raspberry Pi, the u-blox-cfg-loader.py will be run by
udev automatically.

Triggering a Cold Start
~~~~~~~~~~~~~~~~~~~~~~~

As mentioned above in the `GNSS (GNSS Config)`_ section note, u-blox recommends
a cold start after changing the GNSS settings. We can accomplish this by
creating another u-blox configuration file and setting up another udev rule:

.. code-block:: bash

   echo "CFG-RST - 06 04 04 00 FF B9 02 00" | sudo tee -a /etc/u-blox-rst.cfg
   sudo cp udev/60-u-blox-cfg-loader-rst.rules /etc/udev/rules.d

Switching the UART Baud Rate to 115200
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can configure the u-blox UART1 interface to run at a higher baud rate than
the default of 9600. This will not improve the accuracy of the time but will
reduce the chance of a transmit buffer overflow in the u-blox module if you
enable additional messages on the UART1 (ttyAMA0) interface. To change the
baud rate of the UART1 interface on the u-blox module:

* Append the configuration line to the u-center configuration file:

  .. code-block:: bash

     echo "CFG-PRT - 06 00 14 00 01 00 00 00 C0 08 00 00 00 C2 01 00 07 00 03 00 00 00 00 00" | sudo tee -a /etc/u-blox.cfg

* Run the u-blox-cfg-loader.py tool to load your configuration without
  requiring a reboot:

  .. code-block:: bash

     sudo /usr/local/bin/u-blox-cfg-loader.py --port /dev/ttyAMA0 --file /etc/u-blox.cfg

* Update your NTPsec configuration to use 115200 baud:

  .. code-block:: bash

     sudo sed -i 's/9600/115200/g' /etc/ntpsec/ntp.conf

* Restart the NTPsec service:

  .. code-block:: bash

     sudo systemctl restart ntpsec

* Update your ser2net configuration to use 115200 baud:

  .. code-block:: bash

     sudo sed -i 's/ttyAMA0:9600/ttyAMA0:115200/g' /etc/ser2net.conf

* Update the cold start udev rule:

  .. code-block:: bash

     sudo sed -i 's/u-blox-rst.cfg/u-blox-rst.cfg --speed 115200/g' /etc/udev/rules.d/60-u-blox-cfg-loader-rst.rules

Setting up a watchdog timer (Optional)
**************************************

The Raspberry Pi includes a hardware watchdog device that can be used to
reset the Raspberry Pi should the software freeze (such as a kernel panic).

1. Enable the watchdog hardware device:

   * Edit the /boot/firmware/syscfg.txt

     * Add "dtparam=watchdog=on". On reboot, this will enable the watchdog
       device.

2. Install the watchdog system service:

   .. code-block:: bash

      sudo apt-get update
      sudo apt-get install watchdog

3. Configure the watchdog service:

   * Edit the /etc/watchdog.conf file

     * Add "watchdog-device = /dev/watchdog". This will set the location
       of the hardware watchdog device file.
     * Add "watchdog-timeout = 15". This sets the time, in seconds, the
       hardware device will wait for an update before triggering a hardware
       reset.
     * Add "max-load-1 = 24". This is the one-minute load average threshold
       at which the watchdog service will reboot the device. The one-minute
       load average is the first "load average" number when you run the
       "uptime" command. Twenty-four is a large number, approximately six times
       the load a four core Raspberry Pi can normally process.
     * Add "interface = eth0". This will cause the watchdog process to watch
       the "eth0" network interface to make sure it is receiving traffic.
     * Add "temperature-sensor = /sys/class/thermal/thermal_zone0/temp". This
       is the file where the Raspberry Pi core temperature is reported. Note,
       it is reported in thousandths of a degree Celsius.
     * Add "max-temperature = 82". This sets the watchdog service temperature
       threshold to eighty-two degrees Celsius. This is the temperature the
       Raspberry Pi will start throttling the CPU.
     * Add "min-memory = 25000". This sets a minimum available memory threshold
       for the watchdog process. This value is in memory pages, which is 4096
       on the Raspberry Pi (getconf PAGESIZE). A value of twenty-five thousand
       will set a low memory threshold of one hundred megabytes of available
       memory.

4. Enable the watchdog service:

   .. code-block:: bash

      sudo systemctl enable watchdog

5. Reboot the Raspberry Pi to enable the watchdog device:

   .. code-block:: bash

      sudo reboot

6. Verify the watchdog service started successfully:

   .. code-block:: bash

      sudo systemctl status watchdog | less

   The output should show that the service is active (running).


Enabling the u-blox DDC / |I2C| Device (Optional)
**********************************************************

The u-blox CAM-M8C module on the BerryGPS-IMUv3 provides multiple data
interfaces that allow access to the NMEA and UBX protocols. Above we configured
and used the UART interface over the Raspberry Pi hardware serial port (UART).
In addition to the UART interface on the u-blox module, it also supports an
|I2C| compatible Display Data Channel (DDC) interface and a Serial
Peripheral Interface (SPI). On the CAM-M8C module, if the SPI is enabled, the
UART and DDC/|I2C| interfaces cannot be used as they share pins on the
u-blox module. Since I want to use the UART and |I2C| interfaces, I
will not be discussing how to use SPI with the u-blox module.

By enabling the |I2C| interface and making it available to the
Raspberry Pi we can have two, independent, interfaces on the u-blox module.
This allows one interface to be configured to support only the messages
required for our NTP service, and the other can be used to monitor and
configure the u-blox module.

.. _warning:

.. warning::

   Currently the ublox6-gps-i2c driver is not suitable as a source for NTPsec.
   There are occasional delays in producing the NMEA strings from the ttyUBLX0
   device that will cause NTPsec to label it as a falseticker. There are
   adjustments that can be made in the NTPsec configuration file to ignore this
   issue, but this is not good for stability.
   I have also experienced issues attempting to configure the u-blox module
   over the |I2C| device. I recommend using the UART device for configuration
   and NTPsec until the driver can be fixed.

1. Copy over the ublox6-gps-i2c dkms directory:

   .. code-block:: bash

      sudo mkdir /usr/src/ublox6-gps-i2c-1.0
      sudo cp -a ublox6-gps-i2c/* /usr/src/ublox6-gps-i2c-1.0

2. Add the module to dkms so that it will be built for future kernel updates:

   .. code-block:: bash

      sudo dkms add -m ublox6-gps-i2c -v 1.0

3. Build and install the module for the current kernel:

   .. code-block:: bash

      sudo dkms install -m ublox6-gps-i2c -v 1.0

4. Enable the ublox6-gps-i2c kernel module for boot:

   .. code-block:: bash

      echo "ublox6-gps-i2c" | sudo tee -a /etc/modules-load.d/ublox6-gps-i2c.conf

5. Setup udev to enable the ublox_gps |I2C| driver:

   .. code-block:: bash

      sudo cp udev/10.ubox_i2c.rules /etc/udev/rules.d

   Currently the driver doesn't support auto loading the |I2C| driver
   so, I am working around this by setting up a udev rule that detects the
   kernel module loading and tells the |I2C| bus there is a new
   device. Maybe in the future I will update the driver to auto load for this
   i2c bus number and the u-blox |I2C| address. However, that would be
   unsafe as the u-blox module doesn't have any ID registers available to query
   on the |I2C| bus to validate it is the device we want.
 
6. Enable the u-blox i2c device without the need to reboot:

   .. code-block:: bash

      sudo udevadm control --reload
      sudo modprobe ublox6-gps-i2c

   These steps happen automatically on reboot.

7. Optionally update NTPsec to use the |I2C| device:

   * Edit the /etc/ntpsec/ntp.d/refclock.conf file.

     * Change the /dev/ttyAMA0 to /dev/ttyUBLX0 on the "refclock" line.

       .. code-block:: bash

          sudo sed -i 's/ttyAMA0/ttyUBLX0/g' /etc/ntpsec/ntp.d/refclock.conf
          sudo sed -i 's/ baud 9600//g' /etc/ntpsec/ntp.d/refclock.conf

   * Edit the /etc/apparmor.d/tunables/ntpd file.

     * Change the "/dev/ttyAMA0" to "/dev/ttyUBLX0" on the @{NTP_DEVICE} line.

       .. code-block:: bash

          sudo sed -i 's/ttyAMA0/ttyUBLX0/g' /etc/apparmor.d/tunables/ntpd

   * Update the apparmor configuration:

     .. code-block:: bash

        sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.ntpd

   * Restart the ntp service to load the new configuration:

     .. code-block:: bash

        sudo systemctl restart ntpsec

Raspberry Pi 4
**************

Someone was kind enough to gift me a Raspberry Pi 4 (Thank you again!). Here is what I have learned about the Raspberry Pi 4 so far:

U-boot
------

U-boot on Ubuntu 19.10 (eoan) is broken. You cannot do the
"setenv bootdelay -2" trick to stop the GPS serial port from aborting the
boot sequence. This was caused by two issues: my USB keyboard is not
detected by u-boot and the saved environment file is corrupt.

I worked around the USB keyboard issue by using my Raspberry Pi 3 serial port
to access the u-boot serial console on the Raspberry Pi 4.

The issue with the corrupt environment file was a bigger problem. Not only
did it save out without my boot delay change, but it would not load at boot.
I later found out there is an issue in this version with the size of the
u-boot code and the environment data.

In the end, I resorted to building a custom version of u-boot that sets the
autoboot delay and stop strings in u-boot. It would be super nice if Ubuntu
set these by default in the u-boot-rpi package.

1. Download the source files by searching for the correct u-boot-rpi package
   on https://packages.ubuntu.com. There are three files:
   u-boot_2019.07+dfsg-1ubuntu3.dsc, u-boot_2019.07+dfsg.orig.tar.xz, and
   u-boot_2019.07+dfsg-1ubuntu3.debian.tar.xz.

2. Unpack the u-boot_2019.07+dfsg.orig.tar.xz file:

   .. code-block:: bash

      tar xJf u-boot_2019.07+dfsg.orig.tar.xz

3. Go into the new u-boot-2019.07 directory and unpack the debian directory.

   .. code-block:: bash

      cd u-boot-2019.07
      tar xJf ../u-boot_2019.07+dfsg-1ubuntu3.debian.tar.xz

4. Make the required changes to enable the delay and stop strings:

   .. code-block:: bash

      echo "#define CONFIG_AUTOBOOT_KEYED" >> include/configs/rpi.h
      echo "#define CONFIG_AUTOBOOT_DELAY_STR \"delay\"" >> include/configs/rpi.h
      echo "#define CONFIG_AUTOBOOT_STOP_STR \"stop\"" >> include/configs/rpi.h

5. Update the package to include a new patch file for the changes:

   .. code-block:: bash

      dpkg-source --commit

   This will ask for a patch name, I used "rpi4-autoboot-strings". It will then
   open your favorite editor (vim right?) where you can put in a description
   for the patch. Update as you see fit since you will not be distributing it.

6. Build the new u-boot packages:

   .. code-block:: bash

       dpkg-buildpackage -us -uc

   This will take a long time as it rebuilds all of the u-boot packages.

7. Install the newly built package:

   .. code-block:: bash

      sudo dpkg --install ../u-boot-rpi_2019.07+dfsg-1ubuntu3_arm64.deb

The u-blox DDC / |I2C| Device on Raspberry Pi 4
-----------------------------------------------

I am sad to report that the |I2C| bus clock stretching issue that the Raspberry
Pi 3 model B suffers from is still present on the Raspberry Pi 4. I will
continue to use the software/GPIO |I2C| driver on the Raspberry Pi 4.

Raspberry Pi 4 and IEEE 1588 Hardware Timestamping
---------------------------------------------------

Unfortunately the Raspberry Pi 4 ethernet chip does not support IEEE 1588
hardware timestamping. The ethtool output:

.. code-block:: bash

   $ ethtool -T eth0
   Time stamping parameters for eth0:
   Capabilities:
        software-transmit     (SOF_TIMESTAMPING_TX_SOFTWARE)
        software-receive      (SOF_TIMESTAMPING_RX_SOFTWARE)
        software-system-clock (SOF_TIMESTAMPING_SOFTWARE)
   PTP Hardware Clock: none
   Hardware Transmit Timestamp Modes: none
   Hardware Receive Filter Modes: none

For those of you that might be curious about the other offloading capability
on the Raspberry Pi 4, here is default offload settings on Ubuntu 19.10:

.. code-block:: bash

   $ ethtool -k eth0
   Features for eth0:
   rx-checksumming: off
   tx-checksumming: off
        tx-checksum-ipv4: off
        tx-checksum-ip-generic: off [fixed]
        tx-checksum-ipv6: off
        tx-checksum-fcoe-crc: off [fixed]
        tx-checksum-sctp: off [fixed]
   scatter-gather: off
        tx-scatter-gather: off
        tx-scatter-gather-fraglist: off [fixed]
   tcp-segmentation-offload: off
        tx-tcp-segmentation: off [fixed]
        tx-tcp-ecn-segmentation: off [fixed]
        tx-tcp-mangleid-segmentation: off [fixed]
        tx-tcp6-segmentation: off [fixed]
   udp-fragmentation-offload: off
   generic-segmentation-offload: off [requested on]
   generic-receive-offload: on
   large-receive-offload: off [fixed]
   rx-vlan-offload: off [fixed]
   tx-vlan-offload: off [fixed]
   ntuple-filters: off [fixed]
   receive-hashing: off [fixed]
   highdma: off [fixed]
   rx-vlan-filter: off [fixed]
   vlan-challenged: off [fixed]
   tx-lockless: off [fixed]
   netns-local: off [fixed]
   tx-gso-robust: off [fixed]
   tx-fcoe-segmentation: off [fixed]
   tx-gre-segmentation: off [fixed]
   tx-gre-csum-segmentation: off [fixed]
   tx-ipxip4-segmentation: off [fixed]
   tx-ipxip6-segmentation: off [fixed]
   tx-udp_tnl-segmentation: off [fixed]
   tx-udp_tnl-csum-segmentation: off [fixed]
   tx-gso-partial: off [fixed]
   tx-sctp-segmentation: off [fixed]
   tx-esp-segmentation: off [fixed]
   tx-udp-segmentation: off [fixed]
   fcoe-mtu: off [fixed]
   tx-nocache-copy: off
   loopback: off [fixed]
   rx-fcs: off [fixed]
   rx-all: off [fixed]
   tx-vlan-stag-hw-insert: off [fixed]
   rx-vlan-stag-hw-parse: off [fixed]
   rx-vlan-stag-filter: off [fixed]
   l2-fwd-offload: off [fixed]
   hw-tc-offload: off [fixed]
   esp-hw-offload: off [fixed]
   esp-tx-csum-hw-offload: off [fixed]
   rx-udp_tunnel-port-offload: off [fixed]
   tls-hw-tx-offload: off [fixed]
   tls-hw-rx-offload: off [fixed]
   rx-gro-hw: off [fixed]
   tls-hw-record: off [fixed]

Future Work
***********

I would like to try setting this up on the Raspberry Pi 4 platform.
Specifically, to see if I get additional stability out of the 4.

Beyond the Raspberry Pi 4 interests I would like to compare my results on the
u-blox CAM-M8C with other u-blox modules.

U-blox ships the RCB-F9T timing board that should be fairly straight forward to
integrate with a Raspberry Pi. It includes the ZED-F9T "high accuracy timing"
module. I am curious to see the stability improvement this module may bring.

There are also boards available with the ZED-F9P module which is considered a
"high precision GNSS" module.

I am pretty sure that the antenna I am using now is limiting the channels
I am receiving from the GNSS systems. I think this antenna, like most currently
available, filter for the L1 band fairly tightly. U-blox sells a multi-band
external antenna, the ANN-MB-00, that supports the L1 and L2 bands and is
tailored to this usecase. I would be curious to see if this also improves the
stability by using multiple frequencies with different interference/noise.

If you would like to gift me hardware, I have an `Amazon gift wish list available <https://www.amazon.com/hz/wishlist/ls/2XUWE8T9NO87X?ref_=wl_share>`_.

Disclaimers
***********

* Raspberry Pi is a trademark of the Raspberry Pi Foundation
* OzzMaker and BerryGPS-IMUv3 are likely marks owned by OzzMaker
* u-blox is a registered trademark of u-blox Holding AG
* Ubuntu is a registered trademark of Canonical Ltd.
* Broadcom is a registered trademark of Broadcom Inc.
* Adafruit is a registered trademark of Adafruit Industries.
* I did not get compensation from any of these companies for this project.
* This document comes without any warranty of any kind.
* Not intended for safety of life applications.
* The code provided in this repository is licensed under the GNU General
  Public License v3.0. See the included COPYING for terms.
* This document is Copyright 2020 Michael Johnson
* This document is licensed under the Creative Commons Attribution-ShareAlike
  4.0 International Public License

.. raw:: html

   <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-sa/4.0/88x31.png" /></a><br /><span xmlns:dct="http://purl.org/dc/terms/" href="http://purl.org/dc/dcmitype/Text" property="dct:title" rel="dct:type">Create A Raspberry Pi 3 Model B and u-blox CAM-M8C GPS NTP server</span> by <a xmlns:cc="http://creativecommons.org/ns#" href="https://github.com/johnsom" property="cc:attributionName" rel="cc:attributionURL">Michael Johnson</a> is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.
