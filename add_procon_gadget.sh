#!/bin/bash

GADGET="/sys/kernel/config/usb_gadget"
VID="0x057e"                        
PID="0x2009"                        
DEVICE="0x0200"                     
USB_TYPE="0x0200"                   
SERIAL_NUMBER="000000000001"        # serial number
MANUFACTURER="Nintendo Co., Ltd."   # manufacturer code
PRODUCT_NAME="Pro Controller"       # product name
PROTOCOL="0"                        # USB protocol
CLASS="0"                           # USB class
SUBCLASS="0"                        # USB subclass
REPORT_LENGTH="64"                  # USB report length
REPORT_DESCRIPTOR="050115000904A1018530050105091901290A150025017501950A5500650081020509190B290E150025017501950481027501950281030B01000100A1000B300001000B310001000B320001000B35000100150027FFFF0000751095048102C00B39000100150025073500463B0165147504950181020509190F2912150025017501950481027508953481030600FF852109017508953F8103858109027508953F8103850109037508953F9183851009047508953F9183858009057508953F9183858209067508953F9183C0"
DEVICE_NO="usb0"
CONFIG_NO="1"
MAX_POWER="500"
ATTRIBUTES="0xa0"

case "$1" in
    start)
        echo "Creating the USB gadget"
        # modprobe libcomposite       # Loading composite module

        echo "Creating gadget directory"
        cd $GADGET
        mkdir -p procon
        cd procon

        echo "Setting ID's"
        echo $VID > idVendor
        echo $PID > idProduct
        echo $DEVICE > bcdDevice
        echo $USB_TYPE > bcdUSB
        echo $CLASS > bDeviceClass
        echo $SUBCLASS > bDeviceSubClass
        echo $PROTOCOL > bDeviceProtocol

        echo "Creating strings"
        mkdir -p strings/0x409
        echo $SERIAL_NUMBER > strings/0x409/serialnumber
        echo $MANUFACTURER > strings/0x409/manufacturer
        echo $PRODUCT_NAME > strings/0x409/product

        echo "Creating the functions"
        mkdir -p functions/hid.$DEVICE_NO
        echo $PROTOCOL > functions/hid.$DEVICE_NO/protocol
        echo $SUBCLASS > functions/hid.$DEVICE_NO/subclass
        echo $REPORT_LENGTH > functions/hid.$DEVICE_NO/report_length
        echo $REPORT_DESCRIPTOR | xxd -r -ps > functions/hid.$DEVICE_NO/report_desc

        echo "Creating the configurations"
        mkdir -p configs/c.$CONFIG_NO/strings/0x409
        echo "Nintendo Switch Pro Controller" > configs/c.$CONFIG_NO/strings/0x409/configuration
        echo $MAX_POWER > configs/c.$CONFIG_NO/MaxPower
        echo $ATTRIBUTES > configs/c.$CONFIG_NO/bmAttributes

        echo "Associating the functions with their configurations"
        ln -s functions/hid.$DEVICE_NO configs/c.$CONFIG_NO/

        echo "Enabling the USB gadget"
        ls /sys/class/udc > UDC
        echo "OK"
        
        ;;
    stop)
        echo "Stopping the USB gadget"

        echo "Disabling the USB gadget"
        cd $GADGET/procon
        echo "" > UDC

        echo "Cleaning up"
        rm configs/c.$CONFIG_NO/hid.$DEVICE_NO
        rmdir functions/hid.$DEVICE_NO

        echo "Cleaning up configuration"
        rmdir configs/c.$CONFIG_NO/strings/0x409
        rmdir configs/c.$CONFIG_NO

        echo "Clearing strings"
        rmdir strings/0x409

        echo "Removing gadget directory"
        cd $GADGET
        rmdir procon
        cd /

        # modprobe -r libcomposite    # Remove composite module
        echo "OK"

        ;;
    *)
        echo "Usage : $0 {start|stop}"
        ;;
esac