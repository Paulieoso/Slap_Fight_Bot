# webhook_server.py
import logging
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application

from config import config
from bot import SlapFightBot

logger = logging.getLogger(__name__)

class WebhookServer:
    def __init__(self, application: Application):
        self.application = application
        self.bot = application.bot
    
    async def handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming webhook updates"""
        try:
            # Check if the request has the correct content type
            if request.content_type != 'application/json':
                return web.Response(status=400, text="Invalid content type")
            
            # Parse the update
            data = await request.json()
            update = Update.de_json(data, self.bot)
            
            # Process the update
            await self.application.process_update(update)
            
            return web.Response(status=200, text="OK")
        except Exception as e:
            logger.error(f"Error processing webhook update: {e}")
            return web.Response(status=500, text="Internal server error")
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.Response(status=200, text="OK")
    
    async def set_webhook(self) -> bool:
        """Set the webhook with Telegram"""
        try:
            # Set webhook with Telegram
            webhook_url = f"{config.WEBHOOK_URL}{config.WEBHOOK_PATH}"
            
            await self.bot.set_webhook(
                url=webhook_url,
                max_connections=40,
                allowed_updates=["message", "callback_query"]
            )
            
            logger.info(f"Webhook set to: {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
            return False
    
    async def start_server(self):
        """Start the webhook server"""
        # Create aiohttp application
        app = web.Application()
        
        # Add routes
        app.router.add_post(config.WEBHOOK_PATH, self.handle_webhook)
        app.router.add_get('/health', self.health_check)
        
        # Start the server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(
            runner, 
            host=config.WEBHOOK_HOST, 
            port=config.WEBHOOK_PORT
        )
        
        await site.start()
        logger.info(f"Webhook server started on {config.WEBHOOK_HOST}:{config.WEBHOOK_PORT}")
        
        # Set the webhook with Telegram
        await self.set_webhook()
        
        # Keep the server running
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()

async def main():
    """Main function to start the webhook server"""
    try:
        config.validate()
        
        # Initialize the bot application
        application = Application.builder().token(config.BOT_TOKEN).build()
        
        # Set up handlers
        bot = SlapFightBot(config.BOT_TOKEN)
        bot.setup_handlers()
        
        # Initialize the application
        await application.initialize()
        await application.start()
        
        # Start webhook server
        server = WebhookServer(application)
        await server.start_server()
        
    except Exception as e:
        logger.error(f"Failed to start webhook server: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
