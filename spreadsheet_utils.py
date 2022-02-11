# External Imports
from gspread.spreadsheet import Spreadsheet
from re import findall
from typing import List
from distutils.util import strtobool

# Constants
GUILD_FRMT = '[Dd]iscord\s*:*\s*(.+?)(?:$|\n)'
ROLE_FRMT = '[Rr]ole\s*:*\s*(.+?)(?:$|\n)'

def get_spreadsheet_info(spreadsheet: Spreadsheet):
    # Default return object
    sheet_info = None

    # Loop through all sheets (tabs) in spreadsheet to search for format
    worksheet_list = spreadsheet.worksheets()
    if worksheet_list:
        for ws in worksheet_list:
            # Get A1 value 
            A1_value = ws.acell('A1').value
            if not A1_value:
                continue

            # Parse values
            guild_name = findall(GUILD_FRMT, A1_value)
            role_name = findall(ROLE_FRMT, A1_value)

            if len(guild_name) > 0 and len(role_name) > 0:
                sheet_info = {
                    'guild_name': guild_name[0],
                    'role_name': role_name[0],
                    'worksheet': ws
                }
                break

    return sheet_info

def get_row_info(row: List[str]):
    # Default return object
    row_info = None

    # Remove empty cells
    row = [c for c in row if c]

    # Create info if complete row
    if len(row) >= 10:
        name_split = row[5].strip().split('#')
        if len(name_split)  == 2:
            row_info = {
                'member_name': name_split[0],
                'discriminator': name_split[1],
                'approval': bool(strtobool(row[9].strip()))
            }

    return row_info