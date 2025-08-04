import patched_cmd
import os
import argparse
import asyncio
import json
from dotenv import load_dotenv
from openai import OpenAI
from fastmcp import Client


class Colors:
    """String literals of ANSI escape codes for simple colors"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


class CliRpg(patched_cmd.Cmd):
    prompt = f"{Colors.BOLD}{Colors.GREEN}menu){Colors.RESET} "
    intro = f"{Colors.BOLD}Welcome to the CLI RPG game.{Colors.RESET}\nType {Colors.BOLD}\"play\"{Colors.RESET} to start playing.\nType {Colors.BOLD}\"help\"{Colors.RESET} for available commands."

    verbose = False
    in_game = False
    commands = [ 'exit', 'help', 'play', 'print_api_key', 'set_api_key' ] 
    in_game_disabled_commands = [ 'set_api_key', 'play' ]
    
    mcp_client = None
    api_key = None
    openai = None
    messages = []
    available_tools = []
    initial_prompts = None


    def __init__(self, api_key, verbose, mcp_client):
        super().__init__()
        
        if verbose:
            self.verbose = verbose

        if api_key:
            self.log("The api key was passed when creating the CliRpg class instance")
            self.api_key = api_key
        
        if mcp_client:
            self.mcp_client = mcp_client
        else:
            raise Exception("The game client can't function properly without an active connection to the MCP server!")


    def log(self, *args):
        if self.verbose:
            printable_line = " ".join(str(arg) for arg in args)
            print(f"{Colors.BG_WHITE}{Colors.BLACK}{printable_line}{Colors.RESET}")
    

    def do_exit(self, line):
        """Exit the CLI OR exit the game"""
        
        if not self.in_game:
            return True # Exit the program

        self.log(self.messages)

        if self.messages:
            self.messages.clear()

        self.in_game = False
        self.prompt = f"{Colors.BOLD}{Colors.GREEN}menu){Colors.RESET} "

        return False


    async def emptyline(self):
        a = 1 # Needs to do something I think, otherwise a weird bug with async / await happens


    async def process_game_line(self, line, recursive = False):
        # Wrapper function for all things that need doing when the player makes an action or "something" in regards to the game

        # Recursive calls to this function happen when the LLM wants to call a tool on the MCP server, so the line argument is empty thus it shouldn't be put into the message history
        if not recursive:
            self.messages.append({
                "role": "user",
                "content": line
            })

        response = self.openai.chat.completions.create(
            model = "gpt-4.1-nano",
            max_tokens = 100,
            messages = self.messages,
            tools = self.available_tools,
            temperature = 0.2,
            user = "TTRPG Player",
        )

        for choice in response.choices:
            if choice.finish_reason == "tool_calls":
                self.messages.append(choice.message)
                
                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    self.log(f"\nThe LLM wanted to call the {tool_name} tool with args {tool_args}...")
                    result = await self.mcp_client.call_tool(tool_name, tool_args)
                    self.log(f"\nTool response: {result}")
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result.content,
                        }
                    )
                
                await self.process_game_line("", True)

            # elif choice.finish_reason == "stop":
            else:
                self.messages.append({
                    "role": "assistant",
                    "content": choice.message.content
                })
                
                msg = choice.message.content
                if msg.endswith('\n'):
                    msg = msg[:-1]

                print(f"{Colors.BLUE}{Colors.BOLD}Game Master) {Colors.RESET}{Colors.BLUE}{msg}{Colors.RESET}")


    async def default(self, line):
        # Method called on an input line when the command prefix is not recognized
        
        if self.in_game:
            await self.process_game_line(line)
            return

        print(f"{Colors.YELLOW}{Colors.BOLD}{line.split()[0]}{Colors.RESET}{Colors.YELLOW} not recognized as a command!{Colors.RESET}")


    async def precmd(self, line):
        print(f"{Colors.RESET}", end='') # Needed to get rid of the colored text (input) when "playing"

        if self.in_game and len(line) > 0:
            first_word = line.split()[0]
            
            if first_word in self.in_game_disabled_commands:
                print(f"{Colors.YELLOW}The {Colors.BOLD}\"{first_word}\"{Colors.RESET}{Colors.YELLOW} command is disabled when playing!{Colors.RESET}")
                return ''
            
            if first_word in self.commands:
                print(f"{Colors.YELLOW}The word {Colors.BOLD}{first_word}{Colors.RESET}{Colors.YELLOW} was recognized as a command!{Colors.RESET}")
                
                while True:
                    msg = None

                    if first_word == "exit":
                        msg = f"Invoke the {Colors.BOLD}{first_word}{Colors.RESET} command? It will clear the chat history! [y/N] "
                    else:
                        msg = f"Invoke the {Colors.BOLD}{first_word}{Colors.RESET} command? [y/N] "

                    response = input(msg).lower()

                    if response == 'y':
                        return line

                    if len(response) == 0:
                        response = 'n'

                    if response == 'n':
                        await self.process_game_line(line)
                        return ''

        return line
    
    
    def do_set_api_key(self, line):
        """Set the API key for the LLM\nUsage: set_api_key <key>"""

        if len(line) == 0:
            print(f"{Colors.RED}Incorrect usage - {Colors.BOLD}key not given!{Colors.RESET}\nUsage: {Colors.BOLD}set_api_key <key>{Colors.RESET}")
            return
        if len(line.split()) > 1:
            print(f"{Colors.RED}Incorrect usage - {Colors.BOLD}too many words!{Colors.RESET}\nUsage: {Colors.BOLD}set_api_key <key>{Colors.RESET}")
            return

        self.api_key = line
        self.do_print_api_key("")


    def do_print_api_key(self, line):
        """Print the API key for the LLM"""
        print(f"The API key is: {Colors.BOLD}{self.api_key}{Colors.RESET}")


    def do_play(self, line):
        """Start the gameplay
        During the game please write prompts as if you were talking to a real GM
        """

        if not self.api_key:
            print(f"{Colors.BOLD}{Colors.RED}LLM API key not set!{Colors.RESET}")
            return
        
        self.openai = OpenAI(api_key = self.api_key)

        self.in_game = True
        self.prompt = f"{Colors.BOLD}{Colors.GREEN}Player){Colors.RESET}{Colors.GREEN} "


    async def connect_to_mcp_server(self):
        self.log("Trying to ping the server")
        await self.mcp_client.ping()
        self.log("Succesfully ping'ed the server")

        await self.get_initial_prompts()
        await self.get_available_tools()

    
    async def get_initial_prompts(self):
        self.initial_prompts = await self.mcp_client.get_prompt("get_initial_prompts")
        self.log(f"Initial prompts: {self.initial_prompts}")

        messages = []
        for message in self.initial_prompts.messages:
            messages.append({
                "role": message.role,
                "content": message.content.text
            })
        self.messages = messages

    
    async def get_available_tools(self):
        self.log("Fetching available server tools...")
        response = await self.mcp_client.list_tools()
        self.log("Connected to MCP server with tools:", [tool.name for tool in response])

        # Format tools for OpenAI
        available_tools = [
            {
                "type": 'function',
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
                "strict": True,
            }
            for tool in response
        ]
        self.available_tools = available_tools



async def main():
    api_key = None

    parser = argparse.ArgumentParser(
        usage = '%(prog)s [options]',
        description = f"{Colors.BOLD}CLI RPG game client, using an LLM as the game master{Colors.RESET}"
    )
    parser.add_argument('--api_key_file', help = '(Legacy - use .env file) Path to the file with the api key to the LLM')
    parser.add_argument('--api_key', help = '(Legacy - use .env file) The api key to the LLM')
    parser.add_argument('--verbose', action = 'store_true', default = False, help = 'Enable stdout logging')
    args = parser.parse_args()

    if args.api_key_file:
        if not os.path.exists(args.api_key_file):
            print(f"{Colors.RED}The path {Colors.BOLD}{args.api_key_file}{Colors.RESET}{Colors.RED} does not point to a file{Colors.RESET}")
            exit(1)
        
        with open(args.api_key_file, 'r') as file:
            api_key = file.read()

    if args.api_key:
        api_key = args.api_key

    if not api_key:
        load_dotenv()
        api_key = os.getenv("api_key")

    if api_key:
        api_key = api_key.strip()

    # Apparently the MCP server connection (Client(url)) needs to be init'ed in such a way because I tried it the "old-fashioned way" (i.e. client = Client(url)) but it didn't work
    async with Client(os.getenv("MCP_SERVER_URL")) as mcp_client:
        game = CliRpg(api_key, args.verbose, mcp_client)
        await game.connect_to_mcp_server()
        await game.cmdloop()

if __name__ == '__main__':
    asyncio.run(main())