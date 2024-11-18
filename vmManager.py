#!/usr/bin/env python3
import subprocess
import os
import time
import libvirt
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
import hashlib
import pexpect
from utils.utils import getOrCreateISO

class AlpineVMManager:
    def __init__(self, iso_path):
        self.conn = libvirt.open('qemu:///system')
        if self.conn is None:
            raise Exception("Failed to connect to QEMU/KVM")
        
        # Base paths
        self.base_dir = Path('/var/lib/libvirt')
        self.images_dir = self.base_dir / 'images'
        self.shared_dir = self.base_dir / 'shared'
        self.iso_path = iso_path
        
        # Create shared directory if it doesn't exist
        if not self.shared_dir.exists():
            subprocess.run(['sudo', 'mkdir', '-p', str(self.shared_dir)])
            subprocess.run(['sudo', 'chmod', '777', str(self.shared_dir)])
    
    def create_vm(self, name, memory_mb=512, vcpus=1, disk_size_gb=2):
        """Create a new Alpine Linux VM"""
        # Create disk image
        disk_path = self.images_dir / f"{name}.qcow2"
        subprocess.run([
            'sudo', 'qemu-img', 'create', '-f', 'qcow2',
            str(disk_path), f"{disk_size_gb}G"
        ])
        
        # Define VM XML with Alpine specific settings
        xml_config = f"""
        <domain type='kvm'>
            <name>{name}</name>
            <memory unit='MiB'>{memory_mb}</memory>
            <vcpu>{vcpus}</vcpu>
            <os>
                <type arch='x86_64'>hvm</type>
                <boot dev='cdrom'/>
                <boot dev='hd'/>
            </os>
            <features>
                <acpi/>
                <apic/>
            </features>
            <cpu mode='host-passthrough'/>
            <devices>
                <disk type='file' device='disk'>
                    <driver name='qemu' type='qcow2'/>
                    <source file='{disk_path}'/>
                    <target dev='vda' bus='virtio'/>
                </disk>
                <disk type='file' device='cdrom'>
                    <driver name='qemu' type='raw'/>
                    <source file='{self.iso_path}'/>
                    <target dev='hdc' bus='sata'/>
                    <readonly/>
                </disk>
                <filesystem type='mount' accessmode='mapped'>
                    <source dir='{self.shared_dir}'/>
                    <target dir='shared'/>
                </filesystem>
                <interface type='network'>
                    <source network='default'/>
                    <model type='virtio'/>
                </interface>
                <serial type='pty'>
                    <target port='0'/>
                </serial>
                <console type='pty'>
                    <target type='serial' port='0'/>
                </console>
                <graphics type='vnc' port='-1' autoport='yes'/>
            </devices>
        </domain>
        """
        
        domain = self.conn.defineXML(xml_config)
        if domain is None:
            raise Exception(f"Failed to create VM {name}")
        
        domain.create()
        print(f"Created and started VM: {name}")
        return domain
    
    def cleanup(self):
        """Clean up resources and close connection"""
        self.conn.close()

    def automate_alpine_setup(self, vm_name, hostname, keyboard="us", disk_mode="sys", root_password="alpine123"):
        """Automate the Alpine Linux installation process"""
        # Give the VM some time to boot
        time.sleep(10)
        
        # Start the virsh console session
        console = pexpect.spawn(f'virsh console {vm_name}')
        
        try:
            # Initial login
            console.expect('login:', timeout=30)
            console.sendline('root')
            
            # Start setup-alpine
            console.expect('localhost:~#')
            console.sendline('setup-alpine')
            
            # Handle setup questions
            expectations = [
                ("Select keyboard layout", keyboard),
                ("Select variant", keyboard),
                ("Enter system hostname", hostname),
                ("Which one do you want to initialize", "eth0"),  # Select first network interface
                ("Ip address for eth0", "dhcp"),
                ("Do you want to do any manual network configuration", "n"),
                ("New password", root_password),
                ("Retype password", root_password),
                ("Which timezone", "UTC"),
                ("HTTP/FTP proxy URL", "none"),
                ("Which NTP client to run", "chrony"),
                ("Which SSH server", "openssh"),
                ("Which disk\(s\) would you like to use", "vda"),
                ("How would you like to use it", disk_mode),
                ("WARNING: Erase the above disk\(s\) and continue", "y"),
            ]
            
            for expect_text, response in expectations:
                console.expect(expect_text, timeout=30)
                console.sendline(response)
                time.sleep(1)
            
            # Wait for installation to complete
            console.expect('Installation is complete', timeout=300)
            
            # Reboot the system
            console.sendline('reboot')
            
            print(f"Successfully automated setup for VM: {vm_name}")
            
        except pexpect.exceptions.TIMEOUT:
            print(f"Timeout occurred while setting up {vm_name}")
            raise
        finally:
            console.close()

def main():
    if os.geteuid() != 0:
        print("This script needs to be run as root (sudo)")
        return
    
    try:
        # Download Alpine Linux ISO
        iso_path = getOrCreateISO("dl-cdn.alpinelinux.org", "3.20.0", "x86_64")
        
        # Initialize manager with ISO path
        manager = AlpineVMManager(iso_path)
        
        # Create 3 VMs
        vm_configs = [
            {"name": "alpine1", "memory_mb": 512, "vcpus": 1, "disk_size_gb": 2},
            {"name": "alpine2", "memory_mb": 512, "vcpus": 1, "disk_size_gb": 2},
            {"name": "alpine3", "memory_mb": 512, "vcpus": 1, "disk_size_gb": 2}
        ]
        
        vms = []
        for config in vm_configs:
            vm = manager.create_vm(**config)
            vms.append(vm)
        
        print("\nAll Alpine Linux VMs created successfully!")
        print("\nSetup Instructions:")
        print("\n1. For each VM, connect to console:")
        for config in vm_configs:
            print(f"   sudo virsh console {config['name']}")
        
        print("\nShared directory path on host:", manager.shared_dir)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'manager' in locals():
            manager.cleanup()

if __name__ == "__main__":
    main()