KDIR ?= /lib/modules/${kernelver}/build

default:
	$(MAKE) -C $(KDIR) M=$$PWD

install:
	$(MAKE) -C $(KDIR) M=$$PWD modules_install

clean:
	rm -f Module.symvers modules.order *.ko *.mod* *.o
