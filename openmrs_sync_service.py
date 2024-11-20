'''
  OpenMRS - Sender (Local)
  Data Synchronization Script
  ===============================================
  This script runs as a service to manage OpenMRS 
  data synchronization to another
  OpenMRS instance
  --------------------------
  @author:  Kevin Oyowe
  @date:    August 2024 
'''


'''
Import libraries
'''
import mysql.connector
import asyncio
import aiohttp
import logging
import random
import time
from datetime import datetime, date
import os


''' 
Local database connection 
'''
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root1234',
    database='openmrs'
  )



'''
List of tables to sync 
'''
tables_to_sync = [
    'person', 
    'person_address', 
    'person_name', 
    'person_attribute',
    'users',
    'provider',
    'patient',
    'patient_identifier',
    'visit',
    'encounter',
    'encounter_provider',
    'encounter_diagnosis',
    'conditions',
    'allergy',
    'obs'
	]
	
	
	
'''
Cloud server sync api url '''
cloud_url = f"http://50.17.248.213:8000/api/sync/patients"



''' 
local logs configuration 
'''
logging.basicConfig(
  filename='sync_service.log', level=logging.INFO,
  format='%(asctime)s %(levelname)s %(message)s'
  )



logging.info(f"Started OpenMRS sync service")



'''
Local device id
  maybe used to identify
  data coming from this device
'''
def get_device_id():
    if os.path.exists("device_id.txt"):
        with open("device_id.txt", "r") as f:
            return f.read().strip()
    else:
        logging.warning("device_id not found. A new device identity will be created.")
        timestamp = str(int(time.time()))
        new_device_id = f"RAS{timestamp}"
        with open("device_id.txt", "w") as f:
            f.write(new_device_id)
        return new_device_id
        
device_id = get_device_id()
logging.info(f"Device_id ID: {device_id}")



'''
Check tables for sync columns
'''
def check_sync_columns():
    for table in tables_to_sync:
        add_sync_columns(table)


'''
Add sync columns to table
'''
def add_sync_columns(table):
    try:
        cursor = conn.cursor()
        cursor.execute(f"SHOW COLUMNS FROM {table} LIKE 'synced'")
        result = cursor.fetchone()

        if not result:
            alter_query = f"ALTER TABLE {table} ADD COLUMN `synced` INT(11) NULL DEFAULT 0"
            cursor.execute(alter_query)
            conn.commit()
            logging.info(f"Added `synced` column to {table}")

        cursor.close()

    except Exception as e:
        logging.error(f"Error checking/adding `synced` column in {table}: {e}")
        cursor.close()


'''
Fetch database changes
'''                    
async def fetch_changes(table):
    try:
        cursor = conn.cursor(dictionary=True)
        if table == 'person':
            query = """
            -- Check for unsynced or recently changed person related data
            SELECT DISTINCT person.*
            FROM person
                LEFT JOIN person_address ON person.person_id = person_address.person_id
                LEFT JOIN person_name ON person.person_id = person_name.person_id
                LEFT JOIN person_attribute ON person.person_id = person_attribute.person_id
                
                LEFT JOIN users ON person.person_id = users.person_id
                LEFT JOIN provider ON person.person_id = provider.person_id
                
                LEFT JOIN patient ON person.person_id = patient.patient_id
                LEFT JOIN patient_identifier ON person.person_id = patient_identifier.patient_id
                
                LEFT JOIN visit ON person.person_id = visit.patient_id
                LEFT JOIN encounter ON person.person_id = encounter.patient_id
                LEFT JOIN encounter_diagnosis ON person.person_id = encounter_diagnosis.patient_id
                LEFT JOIN conditions ON person.person_id = conditions.patient_id
                LEFT JOIN allergy ON person.person_id = allergy.patient_id
                
                LEFT JOIN obs ON person.person_id = obs.person_id
            WHERE (
                -- person
                person.synced = 0 
                OR (person.date_changed IS NOT NULL AND person.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- person_address
                OR person_address.synced = 0
                OR (person_address.date_changed IS NOT NULL AND person_address.date_changed >= NOW() - INTERVAL 5 MINUTE)

                -- person_name
                OR person_name.synced = 0
                OR (person_name.date_changed IS NOT NULL AND person_name.date_changed >= NOW() - INTERVAL 5 MINUTE)

                -- person_attribute
                OR person_attribute.synced = 0
                OR (person_attribute.date_changed IS NOT NULL AND person_attribute.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- provider
                OR provider.synced = 0
                OR (provider.date_changed IS NOT NULL AND provider.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- users
                OR users.synced = 0
                OR (users.date_changed IS NOT NULL AND users.date_changed >= NOW() - INTERVAL 5 MINUTE)

                -- patient
                OR patient.synced = 0
                OR (patient.date_changed IS NOT NULL AND patient.date_changed >= NOW() - INTERVAL 5 MINUTE)

                -- patient_identifier
                OR patient_identifier.synced = 0
                OR (patient_identifier.date_changed IS NOT NULL AND patient_identifier.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- visit
                OR visit.synced = 0
                OR (visit.date_changed IS NOT NULL AND visit.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- encounter
                OR encounter.synced = 0
                OR (encounter.date_changed IS NOT NULL AND encounter.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- encounter_diagnosis
                OR encounter_diagnosis.synced = 0
                OR (encounter_diagnosis.date_changed IS NOT NULL AND encounter_diagnosis.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- conditions
                OR conditions.synced = 0
                OR (conditions.date_changed IS NOT NULL AND conditions.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- allergy
                OR allergy.synced = 0
                OR (allergy.date_changed IS NOT NULL AND allergy.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- obs
                OR obs.synced = 0
            )
            """
        elif table == 'person_name':
            query = """
            SELECT DISTINCT *, person.uuid as person_uuid FROM person_name 
                JOIN person ON person_name.person_id = person.person_id
            WHERE (
                person_name.synced = 0 
                OR (person_name.date_changed IS NOT NULL AND person_name.date_changed >= NOW() - INTERVAL 5 MINUTE)
            )
            """
        elif table == 'person_attribute':
            query = """
            SELECT DISTINCT *, person.uuid as person_uuid FROM person_attribute
                JOIN person ON person_attribute.person_id = person.person_id
            WHERE (
                person_attribute.synced = 0 
                OR (person_attribute.date_changed IS NOT NULL AND person_attribute.date_changed >= NOW() - INTERVAL 5 MINUTE)
            )
            """
        elif table == 'person_address':
            query = """
            SELECT DISTINCT *, person.uuid as person_uuid FROM person_address
                JOIN person ON person_address.person_id = person.person_id
            WHERE (
                person_address.synced = 0 
                OR (person_address.date_changed IS NOT NULL AND person_address.date_changed >= NOW() - INTERVAL 5 MINUTE)
            )
            """
        elif table == 'users':
            query = """
            SELECT DISTINCT *, users.date_created as data_date_created, users.uuid as data_uuid, person.uuid as person_uuid FROM users
                JOIN person ON users.person_id = person.person_id
                LEFT JOIN provider on users.person_id = provider.person_id
                LEFT JOIN encounter_provider on provider.provider_id = encounter_provider.provider_id
            WHERE (
                users.synced = 0 
                OR (users.date_changed IS NOT NULL AND users.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- provider
                OR provider.synced = 0 
                OR (provider.date_changed IS NOT NULL AND provider.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- encounter_provider
                OR encounter_provider.synced = 0 
                OR (encounter_provider.date_changed IS NOT NULL AND encounter_provider.date_changed >= NOW() - INTERVAL 5 MINUTE)
            )
            """
        elif table == 'provider':
            query = """
            SELECT DISTINCT *, provider.date_created as data_date_created, provider.uuid as data_uuid, person.uuid as person_uuid FROM provider
                JOIN person ON provider.person_id = person.person_id
                LEFT JOIN encounter_provider ON provider.provider_id = encounter_provider.provider_id
            WHERE (
                provider.synced = 0 
                OR (provider.date_changed IS NOT NULL AND provider.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- encounter_provider
                OR encounter_provider.synced = 0
                OR (encounter_provider.date_changed IS NOT NULL AND encounter_provider.date_changed >= NOW() - INTERVAL 5 MINUTE)
            )
            """
        elif table == 'patient':
            query = """
            SELECT DISTINCT *, person.uuid as person_uuid FROM patient
                JOIN person ON patient.patient_id = person.person_id
            WHERE (
                patient.synced = 0 
                OR (patient.date_changed IS NOT NULL AND patient.date_changed >= NOW() - INTERVAL 5 MINUTE)
            )
            """
        elif table == 'patient_identifier':
            query = """
            SELECT DISTINCT *, person.uuid as person_uuid FROM patient_identifier
                JOIN person ON patient_identifier.patient_id = person.person_id
            WHERE (
                patient_identifier.synced = 0 
                OR (patient_identifier.date_changed IS NOT NULL AND patient_identifier.date_changed >= NOW() - INTERVAL 5 MINUTE)
            )
            """
        elif table == 'visit':
            query = """
            SELECT DISTINCT visit.*, person.uuid as person_uuid FROM visit
                JOIN person ON visit.patient_id = person.person_id
                LEFT JOIN encounter ON visit.patient_id = encounter.patient_id
                LEFT JOIN obs ON visit.patient_id = obs.person_id
            WHERE (
                visit.synced = 0 
                OR (visit.date_changed IS NOT NULL AND visit.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- encounter
                OR encounter.synced = 0
                OR (encounter.date_changed IS NOT NULL AND encounter.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- obs
                OR obs.synced = 0
            )
            """
        elif table == 'encounter':
            query = """
            SELECT DISTINCT encounter.*, visit.uuid as visit_uuid FROM encounter
                JOIN visit ON encounter.visit_id = visit.visit_id
                LEFT JOIN encounter_provider ON encounter.encounter_id = encounter_provider.encounter_id
                LEFT JOIN encounter_diagnosis ON encounter.encounter_id = encounter_diagnosis.encounter_id
                LEFT JOIN conditions ON encounter.encounter_id = conditions.encounter_id
                LEFT JOIN obs ON encounter.encounter_id = obs.encounter_id
            WHERE (
                encounter.synced = 0 
                OR (encounter.date_changed IS NOT NULL AND encounter.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- encounter_provider
                OR encounter_provider.synced = 0 
                OR (encounter_provider.date_changed IS NOT NULL AND encounter_provider.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                
                -- encounter_diagnosis
                OR encounter_diagnosis.synced = 0 
                OR (encounter_diagnosis.date_changed IS NOT NULL AND encounter_diagnosis.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- conditions
                OR conditions.synced = 0 
                OR (conditions.date_changed IS NOT NULL AND conditions.date_changed >= NOW() - INTERVAL 5 MINUTE)
                
                -- obs
                OR obs.synced = 0
            )
            """
        elif table == 'encounter_provider':
            query = """
            SELECT DISTINCT *, provider.uuid as provider_uuid, encounter.uuid as encounter_uuid FROM encounter_provider
                JOIN provider ON encounter_provider.provider_id = provider.provider_id
                JOIN encounter ON encounter_provider.encounter_id = encounter.encounter_id
            WHERE (
                encounter_provider.synced = 0 
                OR (encounter_provider.date_changed IS NOT NULL AND encounter_provider.date_changed >= NOW() - INTERVAL 5 MINUTE)
            )
            """
        elif table == 'encounter_diagnosis':
            query = """
            SELECT DISTINCT encounter_diagnosis.*, encounter.uuid as encounter_uuid FROM encounter_diagnosis
                JOIN encounter ON encounter_diagnosis.encounter_id = encounter.encounter_id
            WHERE encounter_diagnosis.synced = 0
            """
        elif table == 'conditions':
            query = """
            SELECT DISTINCT conditions.*, person.uuid as person_uuid FROM conditions
                JOIN person ON conditions.patient_id = person.person_id
            WHERE conditions.synced = 0
            """
        elif table == 'allergy':
            query = """
            SELECT DISTINCT allergy.*, encounter.uuid as encounter_uuid,
            reaction_concept_id, reaction_non_coded, allergy_reaction.uuid as allergy_reaction_uuid 
            FROM allergy
                JOIN encounter ON allergy.patient_id = encounter.patient_id
                JOIN allergy_reaction on allergy.allergy_id = allergy_reaction.allergy_id
            WHERE allergy.synced = 0
            """
        elif table == 'obs':
            query = """
            SELECT DISTINCT obs.*, encounter.uuid as encounter_uuid FROM obs
                JOIN encounter ON obs.encounter_id = encounter.encounter_id
            WHERE obs.synced = 0
            """
        else:
            # Fetch unsynced records for other tables
            query = f"SELECT * FROM {table} WHERE synced = 0"
        
        cursor.execute(query)
        changes = cursor.fetchall()
        cursor.close()
        
        return changes
        
    except Exception as e:
        logging.error(f"Error fetching changes from {table}: {e}")
        return []



'''
Handle date objects
'''
def convert_datetimes_to_strings(data):
    if isinstance(data, dict):
        return {k: convert_datetimes_to_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_datetimes_to_strings(item) for item in data]
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    else:
        return data



'''
Get primary keys
'''
async def get_first_column(table):
    cursor = conn.cursor()
    cursor.execute(f"SHOW COLUMNS FROM {table}")
    columns = cursor.fetchall()
    cursor.close()
    return columns[0][0]



'''
Send data to cloud
'''
async def send_data_to_cloud(device_id, table, data):
    max_retries = 5
    backoff_factor = 2
    payload = {
      "device_id": device_id,
      "table": table,
      "data": convert_datetimes_to_strings(data)
    }
    async with aiohttp.ClientSession() as session:
        for attempt in range(max_retries):
            try:
                logging.info(f"Sending {table} data")
                async with session.post(cloud_url, json=payload) as response:
                    response_data = await response.json()
                    if response.status == 200:
                        if isinstance(response_data, dict) and response_data.get("status") == "success":
                            logging.info(f"Send {table} data : success")
                            return True
                        else:
                            logging.error(f"{table} data could not be processed.")
                            return False
                    else:
                        logging.error(f"Failed with status code: {response.status}")
                        return False
            except aiohttp.ClientError as e:
                logging.error(f"Error sending data from {table} to cloud (attempt {attempt+1}): {e}")
                sleep_time = backoff_factor ** attempt + random.uniform(0, 1)
                logging.info(f"Retrying in {sleep_time:.2f} seconds...")
                await asyncio.sleep(sleep_time)
    return False




'''
Synchronize data
'''
async def sync_task():
    for table in tables_to_sync:
        first_column = await get_first_column(table)
        changes = await fetch_changes(table)
        if changes:
            ids = [change[first_column] for change in changes]
            if await send_data_to_cloud(device_id, table, changes):
                await mark_as_synced(table, ids)
        else:
            logging.info(f"No changes detected for {table}")
        await asyncio.sleep(5)  #5s - please set a reasonable time, preferrably in 15 minutes
    logging.info(f"END - All specified tables have been checked - END")
        


'''
Mark records as synced
'''        
async def mark_as_synced(table, ids):
    try:
        cursor = conn.cursor()
        primary_key = await get_first_column(table)
        placeholders = ', '.join(['%s'] * len(ids))
        query = f"UPDATE {table} SET synced = 1 WHERE {primary_key} IN ({placeholders})"
        cursor.execute(query, tuple(ids))
        conn.commit()
        logging.info(f"Sync updated for table {table}")
        cursor.close()
    except Exception as e:
        logging.error(f"Error marking records as synced in {table}: {e}")
        cursor.close()


      
if __name__ == "__main__":
    check_sync_columns()
    asyncio.run(sync_task())
