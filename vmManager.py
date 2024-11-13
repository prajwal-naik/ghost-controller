import virtualbox
import time
import os
from pathlib import Path
import logging

from utils.utils import getOrCreateISO

logging.basicConfig(level=logging.INFO)

class VMManager:
    def __init__(self, baseMemory=512):
        self.vbox = virtualbox.VirtualBox()
        self.baseMemory = baseMemory
        self.hostPath = os.path.join(os.getcwd(), "sharedDir")

        
        if not os.path.exists(self.hostPath):
            os.makedirs(self.hostPath)

    def create_vm(self, name, osType="Linux_64"):
        """Create a new VM with the specified name and OS type"""
        try:
            vm = self.vbox.create_machine("", name, [], osType, "")

            vm.memory_size = self.baseMemory
            vm.cpu_count = 1
            vm.cpu_property_set("PAE", True)
            vm.bios_settings.io_apic_enabled = True
            self.vbox.register_machine(vm)
            
            session = virtualbox.Session()
            vm.lock_machine(session, virtualbox.LockType.write)
            
            hdd = self.vbox.create_medium("", f"{name}_disk.vdi", 
                                        virtualbox.DeviceType.hard_disk,
                                        virtualbox.AccessMode.read_write)
            
            hdd.variant = virtualbox.MediumVariant.standard | virtualbox.MediumVariant.compressed
            
            hdd.create_base_storage(5 * 1024 * 1024 * 1024)
            
            storage = session.machine.add_storage_controller("SATA", 
                                                          virtualbox.StorageBus.sata)
            session.machine.attach_device(storage.name, 0, 0, 
                                        virtualbox.DeviceType.hard_disk, hdd)
            
            dvdController = session.machine.add_storage_controller("IDE", 
                                                                virtualbox.StorageBus.ide)
            
            # Set up shared folder
            session.machine.create_shared_folder("sharedDir", self.hostPath, 
                                              True, True, "")
            
            # Enable page fusion to reduce memory usage
            session.machine.page_fusion_enabled = True
            
            # Disable audio
            session.machine.audio_adapter.enabled = False
            
            # Configure network adapter for NAT
            adapter = session.machine.get_network_adapter(0)
            adapter.attachment_type = virtualbox.NetworkAttachmentType.nat
            adapter.enabled = True
            
            session.machine.save_settings()
            session.unlock_machine()
            
            return True, f"Successfully created VM: {name}"
            
        except Exception as e:
            return False, f"Failed to create VM: {str(e)}"

    def attach_iso(self, vmName, isoPath):
        """Attach ISO file to VM"""
        try:
            vm = self.vbox.find_machine(vmName)
            session = virtualbox.Session()
            vm.lock_machine(session, virtualbox.LockType.write)
            
            # Attach ISO to IDE controller
            session.machine.attach_device("IDE", 1, 0,
                                        virtualbox.DeviceType.dvd,
                                        session.machine.create_medium_attachment("IDE", 1, 0,
                                        virtualbox.DeviceType.dvd, isoPath))
            
            session.machine.save_settings()
            session.unlock_machine()
            return True, "ISO attached successfully"
        except Exception as e:
            return False, f"Failed to attach ISO: {str(e)}"

    def start_vm(self, name):
        """Start a VM using VirtualBox"""
        try:
            vm = self.vbox.find_machine(name)
            session = virtualbox.Session()
            progress = vm.launch_vm_process(session, "gui", [])
            progress.wait_for_completion()
            return True, f"Successfully started VM: {name}"
        except Exception as e:
            return False, f"Failed to start VM: {str(e)}"




def main():
    # Initialize VM manager with 512MB RAM per VM
    vm_manager = VMManager(baseMemory=512)
    
    # isoPath = "/path/to/alpine-standard-3.19.0-x86_64.iso"
    isoPath = ""
    try:
        isoPath = getOrCreateISO("dl-cdn.alpinelinux.org", "3.20.0", "aarch64")
    except Exception as e:
        logging.info("Error: {e}".format(e = e))
        exit()
    
    # VM names
    vmNames = ["Alpine_VM1", "Alpine_VM2", "Alpine_VM3"]
    
    # Create and start VMs one by one
    for vmName in vmNames:
        logging.info(f"\nCreating {vmName}...")
        success, message = vm_manager.create_vm(vmName)
        logging.info(message)
        
        if success:
            # Attach ISO
            logging.info(f"Attaching Alpine Linux ISO to {vmName}...")
            success, message = vm_manager.attach_iso(vmName, isoPath)
            logging.info(message)
            
            if success:
                logging.info(f"Starting {vmName}...")
                success, message = vm_manager.start_vm(vmName)
                logging.info(message)
            
            # Wait between VM creations
            time.sleep(15)

if __name__ == "__main__":
    main()