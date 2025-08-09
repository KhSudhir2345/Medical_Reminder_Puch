#!/usr/bin/env python3

import os
import json
import uuid
import yaml
import logging
import datetime
import schedule
import threading
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "data"
MEDICINES_FILE = DATA_DIR / "medicines.yaml"
REMINDERS_FILE = DATA_DIR / "reminders.yaml"
ORDERS_FILE = DATA_DIR / "orders.yaml"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Initialize data files if they don't exist
if not MEDICINES_FILE.exists():
    with open(MEDICINES_FILE, 'w') as f:
        yaml.dump({}, f)

if not REMINDERS_FILE.exists():
    with open(REMINDERS_FILE, 'w') as f:
        yaml.dump({}, f)

if not ORDERS_FILE.exists():
    with open(ORDERS_FILE, 'w') as f:
        yaml.dump({}, f)


class MedicineReminder:
    def __init__(self):
        self.medicines = self._load_data(MEDICINES_FILE)
        self.reminders = self._load_data(REMINDERS_FILE)
        self.orders = self._load_data(ORDERS_FILE)
        
        # Start the scheduler in a separate thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Medicine Reminder system initialized")
    
    def _load_data(self, file_path: Path) -> Dict:
        """Load data from YAML file"""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                return data if data else {}
        except Exception as e:
            logger.error(f"Error loading data from {file_path}: {e}")
            return {}
    
    def _save_data(self, data: Dict, file_path: Path) -> bool:
        """Save data to YAML file"""
        try:
            with open(file_path, 'w') as f:
                yaml.dump(data, f)
            return True
        except Exception as e:
            logger.error(f"Error saving data to {file_path}: {e}")
            return False
    
    def _run_scheduler(self):
        """Run the scheduler in a loop"""
        # Check for reminders every hour
        schedule.every().hour.do(self._check_reminders)
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Sleep for 1 minute
    
    def _check_reminders(self):
        """Check for due reminders and send notifications"""
        now = datetime.datetime.now()
        today = now.date()
        current_hour = now.hour
        
        for medicine_id, reminder in self.reminders.items():
            if medicine_id not in self.medicines:
                continue
                
            medicine = self.medicines[medicine_id]
            last_refill_date = parse(medicine.get('last_refill_date', medicine.get('added_date')))
            quantity = medicine.get('quantity', 30)
            refill_period = medicine.get('refill_period_days', 30)
            days_before_empty = reminder.get('days_before_empty', 5)
            reminder_time = reminder.get('reminder_time', '08:00')
            reminder_hour = int(reminder_time.split(':')[0])
            
            # Calculate when medicine will run out
            empty_date = last_refill_date + relativedelta(days=refill_period)
            reminder_date = empty_date - relativedelta(days=days_before_empty)
            
            # Check if reminder is due today at this hour
            if (reminder_date.date() == today and 
                reminder_hour == current_hour and 
                not reminder.get('last_reminded_date') == today.isoformat()):
                
                # Send WhatsApp reminder (simulated for now)
                self._send_whatsapp_reminder(medicine_id)
                
                # Update last reminded date
                self.reminders[medicine_id]['last_reminded_date'] = today.isoformat()
                self._save_data(self.reminders, REMINDERS_FILE)
    
    def _send_whatsapp_reminder(self, medicine_id: str):
        """Send a WhatsApp reminder for medicine refill (simulated)"""
        medicine = self.medicines[medicine_id]
        logger.info(f"Sending WhatsApp reminder for {medicine['name']} ({medicine['dosage']})")
        
        # In a real implementation, this would use a WhatsApp API
        # For now, we just log the reminder
        message = f"Reminder: Your {medicine['name']} ({medicine['dosage']}) will run out soon. Reply 'ORDER {medicine_id}' to place a refill order."
        logger.info(f"WhatsApp message: {message}")
    
    def add_medicine(self, name: str, dosage: str, quantity: int, refill_period_days: int) -> Dict:
        """Add a new medicine to track"""
        medicine_id = f"med_{uuid.uuid4().hex[:8]}"
        today = datetime.datetime.now().date().isoformat()
        
        medicine = {
            'id': medicine_id,
            'name': name,
            'dosage': dosage,
            'quantity': quantity,
            'refill_period_days': refill_period_days,
            'added_date': today,
            'last_refill_date': today
        }
        
        self.medicines[medicine_id] = medicine
        self._save_data(self.medicines, MEDICINES_FILE)
        
        return medicine
    
    def list_medicines(self) -> List[Dict]:
        """List all tracked medicines"""
        return list(self.medicines.values())
    
    def set_reminder(self, medicine_id: str, days_before_empty: int, reminder_time: str) -> Dict:
        """Set or update a reminder for a specific medicine"""
        if medicine_id not in self.medicines:
            raise ValueError(f"Medicine with ID {medicine_id} not found")
        
        reminder = {
            'medicine_id': medicine_id,
            'days_before_empty': days_before_empty,
            'reminder_time': reminder_time,
        }
        
        self.reminders[medicine_id] = reminder
        self._save_data(self.reminders, REMINDERS_FILE)
        
        return reminder
    
    def order_refill(self, medicine_id: str) -> Dict:
        """Place a refill order for a specific medicine"""
        if medicine_id not in self.medicines:
            raise ValueError(f"Medicine with ID {medicine_id} not found")
        
        medicine = self.medicines[medicine_id]
        today = datetime.datetime.now().date().isoformat()
        
        order = {
            'id': f"order_{uuid.uuid4().hex[:8]}",
            'medicine_id': medicine_id,
            'medicine_name': medicine['name'],
            'medicine_dosage': medicine['dosage'],
            'order_date': today,
            'status': 'placed'
        }
        
        # Update medicine's last refill date
        self.medicines[medicine_id]['last_refill_date'] = today
        self._save_data(self.medicines, MEDICINES_FILE)
        
        # Save the order
        order_id = order['id']
        self.orders[order_id] = order
        self._save_data(self.orders, ORDERS_FILE)
        
        return order
    
    def get_upcoming_reminders(self) -> List[Dict]:
        """Get a list of upcoming medication reminders"""
        upcoming = []
        now = datetime.datetime.now()
        today = now.date()
        
        for medicine_id, reminder in self.reminders.items():
            if medicine_id not in self.medicines:
                continue
                
            medicine = self.medicines[medicine_id]
            last_refill_date = parse(medicine.get('last_refill_date', medicine.get('added_date')))
            refill_period = medicine.get('refill_period_days', 30)
            days_before_empty = reminder.get('days_before_empty', 5)
            
            # Calculate when medicine will run out
            empty_date = last_refill_date + relativedelta(days=refill_period)
            reminder_date = empty_date - relativedelta(days=days_before_empty)
            
            # Only include future reminders
            if reminder_date.date() >= today:
                upcoming.append({
                    'medicine_id': medicine_id,
                    'medicine_name': medicine['name'],
                    'medicine_dosage': medicine['dosage'],
                    'reminder_date': reminder_date.date().isoformat(),
                    'empty_date': empty_date.date().isoformat(),
                    'reminder_time': reminder.get('reminder_time', '08:00')
                })
        
        # Sort by reminder date
        upcoming.sort(key=lambda x: x['reminder_date'])
        return upcoming


# Initialize the MedicineReminder system
medicine_reminder = MedicineReminder()

# Define tool functions
def add_medicine(name: str, dosage: str, quantity: int, refill_period_days: int) -> Dict:
    """
    Add a new medicine to track with name, dosage, and refill schedule.
    
    Args:
        name: The name of the medicine
        dosage: The dosage of the medicine (e.g., "10mg")
        quantity: The quantity of pills/units in a refill
        refill_period_days: How many days a refill typically lasts
    """
    return medicine_reminder.add_medicine(name, dosage, quantity, refill_period_days)

def list_medicines() -> List[Dict]:
    """
    List all tracked medicines with their details.
    """
    return medicine_reminder.list_medicines()

def set_reminder(medicine_id: str, days_before_empty: int, reminder_time: str) -> Dict:
    """
    Set or update a reminder for a specific medicine.
    
    Args:
        medicine_id: The ID of the medicine to set a reminder for
        days_before_empty: How many days before running out to send a reminder
        reminder_time: The time of day to send the reminder (format: "HH:MM")
    """
    return medicine_reminder.set_reminder(medicine_id, days_before_empty, reminder_time)

def order_refill(medicine_id: str) -> Dict:
    """
    Place a refill order for a specific medicine.
    
    Args:
        medicine_id: The ID of the medicine to order a refill for
    """
    return medicine_reminder.order_refill(medicine_id)

def get_upcoming_reminders() -> List[Dict]:
    """
    Get a list of upcoming medication reminders.
    """
    return medicine_reminder.get_upcoming_reminders()

# Create FastMCP server
server = FastMCP("Medicine Reminder")

# Register tools with the server
@server.tool(
    name="add_medicine",
    description="Add a new medicine to track with refill reminders."
)
def add_medicine_tool(name: str, dosage: str, quantity: int, refill_period_days: int):
    """Add a new medicine to track with refill reminders."""
    return add_medicine(name, dosage, quantity, refill_period_days)

@server.tool(
    name="list_medicines",
    description="List all tracked medicines."
)
def list_medicines_tool():
    """List all tracked medicines."""
    return list_medicines()

@server.tool(
    name="set_reminder",
    description="Set a reminder for a specific medicine."
)
def set_reminder_tool(medicine_id: str, days_before_empty: int, reminder_time: str):
    """Set a reminder for a specific medicine."""
    return set_reminder(medicine_id, days_before_empty, reminder_time)

@server.tool(
    name="order_refill",
    description="Order a refill for a specific medicine."
)
def order_refill_tool(medicine_id: str):
    """Order a refill for a specific medicine."""
    return order_refill(medicine_id)

@server.tool(
    name="get_upcoming_reminders",
    description="Get a list of upcoming medicine refill reminders."
)
def get_upcoming_reminders_tool():
    """Get a list of upcoming medicine refill reminders."""
    return get_upcoming_reminders()


if __name__ == "__main__":
    logger.info("Starting Medicine Reminder MCP Server")
    import asyncio
    asyncio.run(server.run_stdio_async())