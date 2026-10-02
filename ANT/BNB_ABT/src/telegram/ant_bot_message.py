from utils import config_ANT as config
from telethon import TelegramClient, events
from datetime import datetime
from pytz import timezone
import time, sys, os
import pyscreenshot
from urllib.request import urlopen
import re as r
import psutil
import subprocess
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.utils import db_util
from src.data import DB_Signal_Query as dbsq
import warnings
warnings.filterwarnings('ignore')


start_time = str(datetime.now().strftime("%H:%M:%S"))
print(start_time)

# Reading Configs
# Setting configuration values
api_id = config.api_id
api_hash = str(config.api_hash)

phone = config.phone
username = config.username

# Create the client and connect
client = TelegramClient(username, api_id, api_hash)
batch_script_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../batches/Run_DB_BreakOut_Data.sh")
batch_script_trade = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../batches/Run_DB_BreakOut_Trade.sh")


def take_pic():
    try:
        img = pyscreenshot.grab()
        current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../')
        # Override with the SCR_IMAGES_PATH env var (see batches/_env.sh); defaults to <project>/scr_images/
        img_folder = os.path.join(os.environ.get('SCR_IMAGES_PATH') or os.path.join(current_dir, 'scr_images'), '')
        if not os.path.exists(img_folder):
            os.makedirs(img_folder)
        dt_today = datetime.today()  # Local time
        dt_India = dt_today.astimezone(timezone('Asia/Kolkata'))
        imagename = str(datetime.strftime(dt_India, "%d%m%Y%H%M%S"))
        name = img_folder + imagename + ".png"
        img.save(name)
        return name
    except Exception as ex:
        error_log = str(ex).replace('\'', '\'\'') + " - insert_signal :: line ::" \
                    + str(sys.exc_info()[2].tb_lineno)
        print('Error: - Taken scr error - {}'.format(error_log))
        return ''


def getIP():
    d = str(urlopen('http://checkip.dyndns.com/')
            .read())
    return r.compile(r'Address: (\d+\.\d+\.\d+\.\d+)').\
             search(d).group(1)        
      

# -766017680 - ANT CryptoBot
@client.on(events.NewMessage(chats=-766017680))
async def my_event_handler(event):
    print('ANT CryptoBot: ', event.raw_text)
    if event.raw_text.lower().startswith('hi') or event.raw_text.lower() == 'hi':
        await event.reply('Hi, How can I help you!')
    elif event.raw_text.lower().startswith('screenshot') or event.raw_text.lower() == 'screenshot':
        imgname = take_pic()
        if imgname != '':
            await client.send_file("ANT CryptoBot", imgname, caption="screenshot", link_preview=True)
    elif event.raw_text.lower().startswith('system restart') or event.raw_text.lower() == 'restart':
        os.system("shutdown /r /t 1")
    elif event.raw_text.lower().startswith('myipaddress') or event.raw_text.lower() == 'ipaddress' or event.raw_text.lower() == 'ip address':
        ip_address = getIP()
        await event.reply(ip_address)
    elif event.raw_text.lower().startswith('get process') or event.raw_text.lower() == 'get process':
        for proc in psutil.process_iter():
            if any(procstr in proc.name() for procstr in\
                ['cmd']):
                procdetails = str(f'CMD Process - {proc}')
                await event.reply(procdetails)
    elif event.raw_text.lower().startswith('kill process'):
        proc_pid = event.raw_text.replace('kill process ', '').replace('Kill process ', '').replace('Kill Process ', '')
        if psutil.pid_exists(int(proc_pid)):
            os.kill(pid, signal.SIGTERM);
            procdetails = str(f'Killing {proc_pid}')
            await event.reply(f'{procdetails}')
    elif event.raw_text.lower().startswith('run data') or event.raw_text.lower() == 'run data':
        try:
            subprocess.call(["bash", batch_script_data])
            await event.reply(f'run data started')
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - price_breakOut :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            await event.reply(error_log)
    elif event.raw_text.lower().startswith('run trade') or event.raw_text.lower() == 'run trade':
        try:
            subprocess.call(["bash", batch_script_trade])
            await event.reply(f'run trade started')
        except Exception as ex:
            error_log = str(ex).replace('\'', '\'\'') + " - price_breakOut :: line ::" \
                        + str(sys.exc_info()[2].tb_lineno)
            await event.reply(error_log)

while True:
    try:
        client.start()
        client.run_until_disconnected()
    except:
        continue