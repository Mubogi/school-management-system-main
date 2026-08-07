"""
Hardware ID (HWID) Generation Module
Generates unique machine identifiers for license binding.
"""
import hashlib
import platform
import uuid
import os
import subprocess

def _get_mac_address() -> str:
    """Get the primary MAC address of the machine."""
    mac = uuid.getnode()
    return ':'.join(('%012x' % mac)[i:i+2] for i in range(0, 12, 2))

def _get_cpu_id() -> str:
    """Get CPU identifier."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['powershell', '-Command', 
                "(Get-WmiObject Win32_Processor).ProcessorId"], 
                capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        elif platform.system() == "Linux":
            result = subprocess.run(['cat', '/proc/cpuinfo'], 
                capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'Serial' in line or 'processor' in line:
                    return line.strip()
        # Fallback
        return platform.processor() or 'CPU'
    except Exception:
        return 'UNKNOWN_CPU'

def _get_disk_serial() -> str:
    """Get the main disk serial number."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['powershell', '-Command', 
                "(Get-WmiObject Win32_DiskDrive).SerialNumber"], 
                capture_output=True, text=True, timeout=5)
            return result.stdout.strip()
        elif platform.system() == "Linux":
            result = subprocess.run(['lsblk', '-o', 'SERIAL', '-n'], 
                capture_output=True, text=True, timeout=5)
            return result.stdout.strip().split('\n')[0] if result.stdout else 'UNKNOWN'
    except Exception:
        pass
    return 'UNKNOWN_DISK'

def _get_machine_id() -> str:
    """Get a unique machine identifier using multiple sources."""
    # Combine multiple identifiers
    mac = _get_mac_address()
    cpu = _get_cpu_id()
    disk = _get_disk_serial()
    os_info = f"{platform.system()}-{platform.release()}"
    
    # Create a deterministic string
    raw_id = f"{mac}-{cpu}-{disk}-{os_info}"
    
    # Hash it to create a consistent identifier
    return hashlib.sha256(raw_id.encode()).hexdigest()[:32]

def _get_hardware_id() -> str:
    """
    Generate a formatted Hardware ID (HWID) for license binding.
    Format: XXXX-XXXX-XXXX-XXXX (uppercase alphanumeric)
    """
    raw = _get_machine_id()
    
    # Format as XXXX-XXXX-XXXX-XXXX
    parts = [raw[i:i+4] for i in range(0, min(len(raw), 16), 4)]
    return '-'.join(parts).upper()

def get_hwid_short() -> str:
    """Get a shortened version of HWID for display."""
    full = _get_hardware_id()
    return f"{full[:8]}...{full[-4:]}"

if __name__ == "__main__":
    print("Machine ID:", _get_machine_id())
    print("Hardware ID:", _get_hardware_id())
    print("Short HWID:", get_hwid_short())
