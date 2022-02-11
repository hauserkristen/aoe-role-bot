# External imports
import os
import json
import discord
import gspread
import logging
from discord.ext import tasks
from dotenv import load_dotenv

# Internal imports
from spreadsheet_utils import get_spreadsheet_info, get_row_info
from handled_exception import HandeledException

# Constants
FIRST_DATA_ROW = 5 # ASSUMPTION
DATA_ROW_LEN = 11 # ASSUMPTION
GSHEET_CONFIG_FILE = 'sample_gsheet_config.json'

# Set up logging
logging.basicConfig(level=logging.INFO)

# Read discord token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Read service email
SERVICE_EMAIL = None
with open(GSHEET_CONFIG_FILE) as config_file:
    gsheet_info = json.load(config_file)
    SERVICE_EMAIL = gsheet_info['client_email']

if not SERVICE_EMAIL:
    raise Exception('Cannot start bot, missing properly formated gsheet config.')

# This bot needs members intent This also needs to be configured in discord's application 
# where bot's can be created. Just need Manage Roles as function besides this.
intents = discord.Intents.default()
intents.members = True

# Start Discord client
client = discord.Client(intents=intents)

# Connect to Google Sheets
gspread_client = gspread.service_account(filename=GSHEET_CONFIG_FILE)

# Confirm connection to server
@client.event
async def on_ready():
    print('{} is connected to the following guilds:\n'.format(client.user))

    for g in client.guilds:
        print('{}(id: {})\n'.format(g.name, g.id))

    # List available spreadsheets
    spreadsheets = gspread_client.openall()
    if spreadsheets:
        print('Available spreadsheets:')
        for spreadsheet in spreadsheets:
            print('Title:', spreadsheet.title, 'URL:', spreadsheet.url)
    else:
        print('No spreadsheets available')
        print('Please share the spreadsheet with Service Account email')
        print(gspread_client.auth.signer_email)

    # Start loop
    check_update_roles.start()

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    elif message.content == '!role_bot_help':
        help_message = 'Set up for aoe-role-bot:\n1. When adding bot to discord, bot needs member intent to read through all members'\
            'in the guild. Additionally needs \'Manage Roles\' functionality.\n2. Bot needs to have higher role than any it will assign.'\
            'So if it will assign (Players, Broadcaster) it will need to be below Admins but above Players and Broadcaster roles.\n3. Need '\
            'to share the Spreadsheet with service account: {}\n\nIt is important to remember the '\
            'following assumptions were made:\n1. There is only one data tab/sheet per Google Sheet (In example sheet, ignore Responses and '\
            'Settings are ignored and Broadcasts is the only sheet read.)\n2. Data is on sheet with A1 filled out with proper format.\n3. First '\
            'row of data is row 6.\n4. There will be no blank lines in between filled out line in form.\n5. All errors will be logged in the column'\
            ' to the right of the data table.\n\nCheck connections to Discord servers and Google sheets using: !role_bot_connections. This will '\
            'also display existing roles in the each server.'.format(SERVICE_EMAIL)
        await message.channel.send(help_message, reference=message) 
    elif message.content == '!role_bot_connections':
        connection_message = 'Available Discord Servers:\n'

        # List available guilds with their roles
        for g in client.guilds:
            roles =  ','.join([r.name.replace('@', '') for r in g.roles])
            connection_message += '{} with Roles: {}\n'.format(g.name, roles)

        # List available spreadsheets
        spreadsheets = gspread_client.openall()
        if spreadsheets:
            connection_message += '\nAvailable spreadsheets:\n'
            for spreadsheet in spreadsheets:
                connection_message +=  'Title: {}, URL: {}\n'.format(spreadsheet.title, spreadsheet.url)
        else:
            connection_message += 'No spreadsheets available. Please share the spreadsheet with Service Account email: {}'.format(gspread_client.auth.signer_email)

        # Send message
        await message.channel.send(connection_message, reference=message) 


# Loop for udpdates every hour
@tasks.loop(hours=1)
async def check_update_roles():
    try:
        # Wait for client connection to discord
        if not client.is_ready():
            return

        # Open all spreadsheets
        spreadsheets = gspread_client.openall()
        if spreadsheets:
            for spreadsheet in spreadsheets:
                # Get info if available
                sheet_info = get_spreadsheet_info(spreadsheet)
                if sheet_info:
                    # Check if guild name exists
                    guild = discord.utils.find(lambda g: g.name == sheet_info['guild_name'], client.guilds)

                    # Update roles
                    if guild:
                        await update_roles(guild, sheet_info)
                    else:
                        # Update cell that existing guild was not found
                        sheet_info['worksheet'].update_cell(FIRST_DATA_ROW, DATA_ROW_LEN+1, 'Bot does not have access to Discord Server: {}'.format(sheet_info['guild_name']))
    except Exception as exception:
        he = HandeledException(exception)
        logging.exception(he.print_exception())

async def update_roles(guild: discord.guild.Guild, sheet_info: dict):
    # Get roles in this guild
    role = discord.utils.find(lambda r: r.name == sheet_info['role_name'], guild.roles)
    if not role:
        # Update cell that existing role was not found
        sheet_info['worksheet'].update_cell(FIRST_DATA_ROW, DATA_ROW_LEN+1, 'Role was not found in Discord Server: {}'.format(sheet_info['role_name']))
        return
    elif sheet_info['worksheet'].cell(FIRST_DATA_ROW, DATA_ROW_LEN+1).value is not None:
        # Check for previous error message
        sheet_info['worksheet'].update_cell(FIRST_DATA_ROW, DATA_ROW_LEN+1, '')

    # Get table data
    records = sheet_info['worksheet'].get_all_values()
    records = records[FIRST_DATA_ROW:]

    # Identify start of table and loop through entries
    for row_num, row in enumerate(records):
        # Ensure row has the minimum correct number of fields
        if len(row) < DATA_ROW_LEN:
            continue

        # Parse discord name and approval from line
        row_info = get_row_info(row)

        # Break if no additional records are found
        # ASSUMPTION: No blank lines between valid lines
        if not row_info:
            break

        # Get memebr
        member = discord.utils.find(lambda m: m.name == row_info['member_name'] and m.discriminator == row_info['discriminator'], guild.members)

        if not member:
            # Update cell that user was not found in guild
            # ASSUMPTION: Error message goes in L5
            sheet_info['worksheet'].update_cell(row_num+FIRST_DATA_ROW+1, DATA_ROW_LEN+1, 'User was not found in Discord Server: {}#{}'.format(row_info['member_name'], row_info['discriminator']))
            continue

        # Check that status matches
        if role in member.roles and not row_info['approval']:
            # Remove role
            await member.remove_roles(role)
        elif role not in member.roles and row_info['approval']:
            # Add role
            await member.add_roles(role)

        # Check for previous error message at header and individual row
        if sheet_info['worksheet'].cell(FIRST_DATA_ROW, DATA_ROW_LEN+1).value is not None:
            sheet_info['worksheet'].update_cell(FIRST_DATA_ROW, DATA_ROW_LEN+1, '')
        if sheet_info['worksheet'].cell(row_num+FIRST_DATA_ROW+1, DATA_ROW_LEN+1).value is not None:
            sheet_info['worksheet'].update_cell(row_num+FIRST_DATA_ROW+1, DATA_ROW_LEN+1, '')
        
    return

client.run(TOKEN)
