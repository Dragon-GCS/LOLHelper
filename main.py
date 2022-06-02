import asyncio
import ssl
import sys

from loguru import logger
from websockets.client import connect
from websockets.exceptions import ConnectionClosedError

from helper.gui import UI
from helper.lcu import LcuClient
from helper.exceptions import GameStart, GameEnd

logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:^10} | {message}</level>")


async def monitor_client(client: LcuClient):
    url = client.base_url.replace("https", "wss")
    async with connect(url, ssl=ssl.SSLContext(), timeout=3) as socket:
        logger.info("启动客户端监听")
        await socket.send(b"[5, \"OnJsonApiEvent\"]")
        while True:
            if resp := await socket.recv():
                client.handle_ws_response(resp)

def main():
    client = LcuClient()
    while True:
        try:
            asyncio.run(monitor_client(client))
        except ConnectionClosedError:
            logger.info("客户端会话关闭, 正在重新连接...")
        except GameStart:
            logger.info("对局已启动")
        except GameEnd:
            logger.info("对局已结束")
        except ConnectionRefusedError:
            logger.info("客户端未启动")
            break
        except Exception as e:
            logger.exception(e)

if __name__ == '__main__':
    ui = UI(main)
    ui.mainloop()
