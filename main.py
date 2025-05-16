import asyncio
import ssl
import sys

from httpx import HTTPStatusError
from loguru import logger
from websockets import connect
from websockets.exceptions import ConnectionClosedError

from helper.exceptions import GameEnd, GameStart
from helper.gui import UI
from helper.lcu import LcuClient

logger.remove()
if sys.stdout is not None:
    logger.add(sys.stdout)


async def monitor_client(client: LcuClient):
    url = client.base_url.replace("https", "wss")
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with connect(url, ssl=ssl_context, open_timeout=3) as socket:
        logger.info("启动客户端监听")
        await socket.send(b'[5, "OnJsonApiEvent_lol-gameflow_v1_gameflow-phase"]')
        await socket.send(b'[5, "OnJsonApiEvent_lol-champ-select_v1_session"]')
        while True:
            if resp := await socket.recv():
                await client.handle_ws_response(resp)


async def main():
    client = LcuClient()
    await client.get_summoner_info()
    while True:
        try:
            await monitor_client(client)
        except ConnectionClosedError:
            logger.info("客户端会话关闭, 正在重新连接...")
        except GameStart:
            logger.info("对局已启动")
        except GameEnd:
            logger.info("对局已结束")
        except HTTPStatusError:
            logger.exception("游戏状态错误")
        except ConnectionRefusedError:
            logger.info("客户端已关闭")
            break
        except Exception:
            logger.exception("Unexpected error")
            break
    print("exit")


if __name__ == "__main__":
    ui = UI(lambda: asyncio.run(main()))
    ui.mainloop()
