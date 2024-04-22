import logging, pytz
from aiogram import Bot, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

TOKEN = "bot_token"
allowed_chat_ids = ["chat_id_group"]
text_waiting = "Waiting Input Data..."
text_success = "Data inserted successfully!"
text_error = "Error creating alternative page. Please try again."

CREDENTIALS_FILE = "file.json"
SPREADSHEET_ID = "id_gshet"
WORKSHEET_NAME = "name worksheet"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

dp.middleware.setup(LoggingMiddleware())

creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
sheets_service = build('sheets', 'v4', credentials=creds)

async def mbotix_gsheet_input(nama: str, profit: str) -> None:
    try:
        print("Inserting data to spreadsheet...")
        indonesia_timezone = pytz.timezone('Asia/Jakarta')
        current_datetime = datetime.now(indonesia_timezone).strftime('%Y-%m-%d %H:%M:%S')

        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{WORKSHEET_NAME}!A:C').execute()

        new_data = [
            [nama, current_datetime, profit]
        ]

        values = result.get('values', []) + new_data

        body = {
            'values': values
        }

        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{WORKSHEET_NAME}!A:C',
            valueInputOption='RAW',
            body=body).execute()

        print(f"{result.get('updatedCells')} cells updated.")

        return current_datetime
    except Exception as e:
        print(f"Error in mbotix_gsheet_input: {e}")
        raise e

async def get_data_for_current_day() -> str:
    try:
        indonesia_timezone = pytz.timezone('Asia/Jakarta')
        current_datetime = datetime.now(indonesia_timezone)

        print(f"Current DateTime: {current_datetime}")
        spreadsheet = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{WORKSHEET_NAME}!A:C').execute()
        values = spreadsheet.get('values', [])

        for row in values[1:]:
            try:
                stored_datetime = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')
                if current_datetime - timedelta(minutes=1) <= stored_datetime <= current_datetime + timedelta(minutes=1):
                    nama, _, profit = row
                    return f"{nama}\nProfit: {profit}"
            except ValueError as e:
                print(f"Error parsing datetime from row: {row}, Error: {e}")

        return "No data found for the current day."
    except Exception as e:
        print(f"Error in get_data_for_current_day: {e}")
        return f"Error fetching data for the current day: {e}"

async def mbotixpros(nama: str, profit: str, chat_id: str) -> None:
    try:
        if not await is_waiting_message_sent(chat_id):
            waiting_message = await send_waiting_message(chat_id)

            timestamp = await mbotix_gsheet_input(nama, profit)
            
            indonesia_timezone = pytz.timezone('Asia/Jakarta')
            current_day_data = await get_data_for_current_day(indonesia_timezone)

            sheet_link = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"

            success_message = (
                f"✅ <b>{text_success}</b>\n\n"
                f"👤 <b>Nama:</b> {nama}\n"
                f"💰 <b>Profit:</b> <code>{profit}</code>\n"  
                f"📅 <b>Date Time:</b> {timestamp}\n\n"
                f"<a href='{sheet_link}'>🌐 <b>You can view the Google Sheet here</b> </a>"
            )

            await bot.edit_message_text(success_message, chat_id, waiting_message.message_id, parse_mode='HTML')
            await remove_waiting_message(chat_id, waiting_message.message_id)
        else:
            timestamp = await mbotix_gsheet_input(nama, profit)

            current_day_data = await get_data_for_current_day()
            sheet_link = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"

            success_message = (
                f"✅ <b>{text_success}</b>\n\n"
                f"👤 <b>Nama:</b> {nama}\n"
                f"💰 <b>Profit:</b> <code>{profit}</code>\n" 
                f"📅 <b>Date Time:</b> {timestamp}\n\n"
                f"<a href='{sheet_link}'>🌐 <b>You can view the Google Sheet here</b> </a>"
            )

            await bot.send_message(chat_id, success_message, parse_mode='HTML')
    except Exception as e:
        print(f"Error in process_and_insert_data: {e}")

async def send_waiting_message(chat_id: str) -> types.Message:
    return await bot.send_message(chat_id, text_waiting)

async def remove_waiting_message(chat_id: str, message_id: int) -> None:
    await bot.delete_message(chat_id, message_id)
    
async def send_success_message(chat_id: str, message_id: int, sheet_link: str) -> None:
    success_message = f"{text_success}\n\nYou can view the Google Sheet here: {sheet_link}"
    await bot.edit_message_text(success_message, chat_id, message_id)

async def is_waiting_message_sent(chat_id: str) -> bool:
    return True

async def editeuy(username: str, new_amount: str, new_crypto: str) -> None:
    try:
        indonesia_timezone = pytz.timezone('Asia/Jakarta')
        current_datetime = datetime.now(indonesia_timezone).strftime('%Y-%m-%d %H:%M:%S')

        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{WORKSHEET_NAME}!A:D').execute()

        values = result.get('values', [])
        if not values:
            print('No data found.')
            return

        updated = False
        for i, row in enumerate(values):
            if len(row) >= 3 and row[0] == username:
                row[1] = current_datetime
                row[2] = new_amount + ' ' + new_crypto
                updated = True
                break

        if updated:
            body = {'values': values}

            result = sheets_service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range=f'{WORKSHEET_NAME}!A:D',
                valueInputOption='RAW',
                body=body).execute()

            print(f"Data for {username} edited successfully.")
            print(f"{result.get('updatedCells')} cells updated.")
        else:
            print(f"Username '{username}' not found in the spreadsheet.")
    except Exception as e:
        print(f"Error in edit_data_in_spreadsheet: {e}")
        raise e

@dp.message_handler(commands=['edit'])
async def handle_edit_command(message: types.Message):
    try:
        print(f"Processing /edit command: {message.text} from chat ID: {message.chat.id}")

        if str(message.chat.id) in allowed_chat_ids:
            command_args = message.text.split()[1:]

            if len(command_args) >= 3:
                username_to_edit = command_args[0]
                new_amount = command_args[1]
                new_crypto = command_args[2].upper()

                await editeuy(username_to_edit, new_amount, new_crypto)

                confirmation_message = f"Data for {username_to_edit} edited successfully."
                await bot.send_message(message.chat.id, confirmation_message)
            else:
                invalid_format_message = "Invalid /edit command format. Expected format: '/edit username new_amount new_crypto'"
                await bot.send_message(message.chat.id, invalid_format_message)
        else:
            unauthorized_message = "Unauthorized access. This command is not allowed for this chat ID."
            await bot.send_message(message.chat.id, unauthorized_message)
    except Exception as e:
        error_message = f"Error in handle_edit_command: {e}"
        print(error_message)
        await bot.send_message(message.chat.id, error_message)

@dp.message_handler(commands=['show'])
async def handle_show_command(message: types.Message):
    try:
        print(f"Processing /show command: {message.text} from chat ID: {message.chat.id}")

        if str(message.chat.id) in allowed_chat_ids:
            data = await shadashow()
            await bot.send_message(message.chat.id, data)
        else:
            unauthorized_message = "Unauthorized access. This command is not allowed for this chat ID."
            await bot.send_message(message.chat.id, unauthorized_message)
    except Exception as e:
        error_message = f"Error in handle_show_command: {e}"
        print(error_message)
        await bot.send_message(message.chat.id, error_message)

async def shadashow() -> str:
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{WORKSHEET_NAME}!A:C').execute()

        values = result.get('values', [])
        data = "\n".join([", ".join(row) for row in values])

        return data
    except Exception as e:
        print(f"Error in shadashow: {e}")
        return "Error fetching data from Google Sheet."

@dp.message_handler(commands=['delete_user'])
async def handle_delete_user_command(message: types.Message):
    try:
        print(f"Processing /delete_user command: {message.text} from chat ID: {message.chat.id}")

        if str(message.chat.id) in allowed_chat_ids:
            command_args = message.text.split()[1:]

            if len(command_args) >= 1:
                username_to_delete = command_args[0]

                await humairadel(username_to_delete, message)

            else:
                invalid_format_message = "Invalid /delete_user command format. Expected format: '/delete_user username'"
                await bot.send_message(message.chat.id, invalid_format_message)
        else:
            unauthorized_message = "Unauthorized access. This command is not allowed for this chat ID."
            await bot.send_message(message.chat.id, unauthorized_message)
    except Exception as e:
        error_message = f"Error in handle_delete_user_command: {e}"
        print(error_message)
        await bot.send_message(message.chat.id, error_message)

async def humairadel(username: str, message: types.Message) -> None:
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{WORKSHEET_NAME}!A:C').execute()

        values = result.get('values', [])

        updated_values = [row for row in values if row[0].strip().lower() != username.strip().lower()]

        if not updated_values:
            updated_values.append([])

        body = {
            'values': updated_values
        }

        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f'{WORKSHEET_NAME}!A:C',
            valueInputOption='RAW',
            body=body).execute()

        print(f"{result.get('updatedCells')} cells updated.")
        confirmation_message = f"Data for {username} deleted successfully."
        await bot.send_message(message.chat.id, confirmation_message)
    except Exception as e:
        print(f"Error in delete_user_from_spreadsheet: {e}")
        raise e

@dp.message_handler(commands=['help'])
async def handle_help_command(message: types.Message):
    try:
        print(f"Processing /help command from chat ID: {message.chat.id}")

        help_message = (
            "<b>Available Commands:</b>\n\n"
            "/input name amount crypto - Input data into Google Sheet\n"
            "/edit username new_amount new_crypto - Edit data in Google Sheet\n"
            "/delete_user username - Delete user data from Google Sheet\n"
            "/show - Show data from Google Sheet\n"
        )

        await bot.send_message(message.chat.id, help_message, parse_mode='HTML')
    except Exception as e:
        error_message = f"Error in handle_help_command: {e}"
        print(error_message)
        await bot.send_message(message.chat.id, error_message)

crypto_symbols = ['BTC', 'ETH', 'TRX', 'BNB', 'LTC', 'DOGE', 'BUSD', 'XRP', 'EOS', 'UNI', 'SHIB', 'USDT', 'BCH', 'ADA', 'DOT', 'LINK', 'MATIC', 'XLM', 'ETC', 'VET', 'SOL', 'FIL', 'TRON', 'CAKE', 'ATOM', 'XEM', 'DOGE', 'ALGO', 'XTZ', 'WBTC', 'USDC', 'DAI', 'AAVE', 'AVAX', 'SUSHI', 'UNI', 'SNX', 'MKR', 'COMP', 'ICX', 'FTT', 'HOT', 'OKB', 'DASH', 'YFI', 'EOS', 'THETA', 'BTT', 'REV', 'BAND', 'SRM', 'HT', 'CEL', 'CRV', 'YFII', 'CHZ', 'NEO', 'BUSD', 'MATIC', 'CELO', 'XMR', 'MIOTA', 'LEO', 'DCR', 'MANA', 'STX', 'LEND', 'WAVES', 'TFUEL', 'ZRX', 'LUNA', 'YF-DAI', 'XTZ', 'RUNE', 'FTM', 'DGB', 'ZEC', 'ENJ', 'REN', 'GRT', 'KSM', 'NANO', 'DENT', 'MIR', 'RVN', 'HNT', 'LSK', 'OMG', 'ONE', 'FLOW', 'SXP', 'QTUM', 'WIN', 'NEXO', 'ONT', 'IOST', 'TUSD', 'ZIL', 'STPT', 'VGX', 'OGN', 'GNO', 'PERL', 'CELR', 'ANKR', 'MANA', 'REN', 'RSR', 'RLC', 'CRO', 'SRM', 'SAND', 'NMR', 'KAVA', 'LRC', 'FTT', 'BNT', 'REP', 'OXT', 'CGLD', 'NKN', 'ARDR', 'ANT', 'BAL', 'BTCST', 'DODO', 'JST', 'KEEP', 'KNC', 'TOMO', 'WIN', 'CHR', 'INR', 'FTM', 'LPT', 'GRT', 'WAXP', 'PHA', 'SNT', 'STMX', 'ORN', 'FUN', 'BAND', 'MAID', 'BZRX', 'NBS', 'TRX', 'HOT', 'STPT', 'DOCK', 'MATIC', 'WOO', 'OCEAN', 'IRIS', 'AMPL', 'LTC', 'SOLVE', 'KAI', 'YFII', 'OXT', 'ELF', 'CTSI', 'YFI', 'GNO', 'LINA', 'CELR', 'STRAX', 'NKN', 'MTL', 'STMX', 'DGB', 'IOST', 'MIR', 'WIN', 'KAVA', 'ZIL', 'IDEX', 'USDC', 'NMR', 'ONG', 'STPT', 'STX', 'ANKR', 'HNS', 'TFUEL', 'OGN', 'MANA', 'SRM', 'CVP', 'CEL', 'XVG', 'RIF', 'FTT', 'IOST', 'HMR', 'BAL', 'LRC', 'DREP', 'KMD', 'ARDR', 'KIN', 'QTUM', 'GNO', 'ORN', 'RSR', 'WTC', 'RLC', 'RPL', 'DOGE', 'JST', 'BEAM', 'GAS', 'OGN', 'BTCST', 'YF-DAI', 'FTM', 'GRIN', 'REPV2', 'SAND', 'VITE', 'FLOW', 'FUN', 'MAID', 'BZRX', 'GNT', 'STPT', 'CRV', 'TROY', 'WBTC', 'GRT', 'LSK', 'DENT', 'RVN', 'MANA', 'WAXP', 'OGN', 'GNO', 'ANT', 'REP', 'ANKR', 'NMR', 'BNT', 'REN', 'BAL', 'DOCK', 'HOT', 'HNS', 'MTL', 'DGB', 'CEL', 'LOOM', 'ETC', 'SKL', 'SOLVE', 'CHZ', 'DREP', 'KAVA', 'SNX', 'SNT', 'QKC', 'STMX', 'OGN', 'VITE', 'POA', 'RIF', 'SPND', 'MANA', 'ANT', 'REP', 'REN', 'ANKR', 'HOT', 'OCEAN', 'CVC', 'COTI', 'DCR', 'DOGE', 'HNT', 'HUM', 'ETC', 'MANA', 'NKN', 'RSR', 'ARPA', 'BAL', 'HMR', 'KAVA', 'DENT', 'SKL', 'RVN', 'MIR', 'POA', 'ANT', 'CVC', 'SPND', 'MANA', 'KNC', 'BAND', 'DGB', 'HMR', 'REN', 'BAL', 'OMG', 'GNT', 'POA', 'KAVA', 'STMX', 'ANT', 'MANA', 'REN', 'BAND', 'HMR', 'ZRX', 'CEL', 'MIR', 'DGB', 'STMX', 'VITE', 'QKC', 'TROY', 'OMG', 'ETC', 'HNT', 'IOST', 'DOGE', 'LUNA', 'QNT', 'OCEAN', 'LTC', 'RSR', 'GNO', 'ARDR', 'KAVA', 'REN', 'BAL', 'SKL', 'ZRX', 'ANT', 'SOLVE', 'HOT', 'ZIL', 'HNT', 'FTT', 'LRC', 'LOOM', 'VITE', 'DGB', 'ETC', 'MANA', 'RVN', 'NKN', 'BAL', 'HMR', 'SNX', 'GNT', 'ARDR', 'REN', 'QKC', 'OMG', 'BAND', 'HNT', 'SKL', 'ZRX', 'SOLVE', 'ZIL', 'LTC', 'ANT', 'HOT', 'LRC', 'DOGE', 'FTT', 'QNT', 'LUNA', 'VITE', 'GNO', 'BNT', 'DGB', 'MANA', 'HMR', 'BAL', 'ARDR', 'HNT', 'SKL', 'NKN', 'REN', 'LOOM', 'ZRX']

@dp.message_handler(commands=['input'])
async def handle_input_command(message: types.Message):
    try:
        print(f"Processing /input command: {message.text} from chat ID: {message.chat.id}")

        if str(message.chat.id) in allowed_chat_ids:
            command_args = message.text.split()[1:]

            if len(command_args) >= 3:
                nama = command_args[0]
                amount = command_args[1]
                crypto = command_args[2].upper() 
                if crypto in crypto_symbols:
                    profit = f"{amount} {crypto}"

                    waiting_message = await send_waiting_message(str(message.chat.id))

                    await mbotixpros(nama, profit, str(message.chat.id))

                    await remove_waiting_message(str(message.chat.id), waiting_message.message_id)
                else:
                    print("Invalid crypto symbol. Allowed symbols are:", crypto_symbols)
            else:
                print("Invalid /input command format. Expected format: '/input nama jumlah kripto'")
    except Exception as e:
        print(f"Error in handle_input_command: {e}")

if __name__ == "__main__":
    try:
        from aiogram import executor
        executor.start_polling(dp, skip_updates=True)
    except Exception as e:
        print(f"Error in main: {e}")
