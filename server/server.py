from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

import os
import dotenv
import argparse
import uvicorn

from database import Database

# TERMINAL
# For instance: python.exe server.py --host 127.0.0.1 --port 8080

validated_path = None
combined_path = ""

dotenv.load_dotenv()
initial_prompt_file_path = os.getenv("INITIAL_PROMPT_FILE_PATH")

if not initial_prompt_file_path:
    raise RuntimeError("INITIAL_PROMPT_FILE_PATH is not set in .env file")

if os.path.exists(initial_prompt_file_path):
    validated_path = initial_prompt_file_path
else:
    local_dir_path = os.path.dirname(os.path.abspath(__file__))
    combined_path = os.path.join(local_dir_path, initial_prompt_file_path)
    if os.path.exists(combined_path):
        validated_path = combined_path

if not validated_path:
    raise RuntimeError(f"Initial prompt file not found at {initial_prompt_file_path} or {combined_path}")

initial_prompt = ""
with open(validated_path, "r") as file:
    initial_prompt = file.read()
    initial_prompt = "\n".join(line for line in initial_prompt.splitlines() if line.strip())

db = Database(db_name=os.path.join(os.path.dirname(os.path.abspath(__file__)), "rpg_database.db"))

g_verbose = False
def log(*args):
    if g_verbose:
        print(f"{args}")

mcp_app = FastMCP(
    name="RPG MCP", 
    dependencies=[],
    instructions="Your responses should be shorter than 300 characters" #customize the model’s behavior globally
)

@mcp_app.tool()
async def query_playable_characters(action: str = "all", id: int = -1) -> str:
    """
    Read info on all existing playable characters from the DB or read info on a specific character by ID.
    action: 'all' or 'by_id'
    id: used only for 'by_id' action
    """
    try:
        if action == "all":
            log(f"query_characters (all) was called")
            c = db.execute_read("SELECT * FROM characters")
            rows = c.fetchall()
            # return "\n".join(str(row) for row in rows)
            characters = ""
            for row in rows:
                characters += f"Character's name: {row['name']}, character's id: {row['id']}, character's class: {row['class']}, character's race: {row['race']}, character's HP: {row['hitpoints']}\n"
            return characters
        elif action == "by_id" and id >= 0:
            log(f"query_characters (by_id) was called")
            c = db.execute_read("SELECT * FROM characters WHERE id = ?", (id,))
            row = c.fetchone()
            # return str(row) if row else "No character found."
            return f"Character's name: {row['name']}, character's id (secret): {row['id']}, character's class: {row['class']}, character's race: {row['race']}, character's HP: {row['hitpoints']}\n" if row else "No character found."
        else:
            log(f"query_characters was called but it failed!")
            return "Invalid action or missing parameters."
    except Exception as e:
        log(f"query_characters was called, but an exception occurred")
        return f"DB Error: {e}"
    
@mcp_app.tool()
async def create_and_add_new_character(name: str = "", class_name: str = "", race: str = "", hitpoints: int = -1) -> str:
    """
    Create a new playable character, and save it in the DB.
    name: name of the character
    class_name: class of the character (e.g., Warrior, Mage, Crossbowman Madman)
    race: race of the character (e.g., Human, Elf)
    hitpoints: initial hitpoints of the character
    """
    try:
        log(f"create_and_add_new_character was called with the following args: name: {name}, class_name: {class_name}, race: {race}, hitpoints: {hitpoints}")
        db.execute_write("INSERT INTO characters (name, class, race, hitpoints) VALUES (?, ?, ?, ?)",
                            (name, class_name, race, hitpoints))
        new_id = db.connection.execute("SELECT id FROM characters WHERE name = ? AND class = ? AND race = ? AND hitpoints = ?", (name, class_name, race, hitpoints)).fetchone()[0]
        return f"Character named {name} created successfully. Character ID is: {new_id}"
    except Exception as e:
        log(f"create_and_add_new_character was called but an exception occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def update_character_hitpoints(id: int = -1, hitpoints: int = -1) -> str:
    """
    Update the current hitpoints of a character, save that info in the DB.
    This is useful to save the character's hitpoints each time it takes damage or heals.
    id: unique identifier for the character
    hitpoints: new hitpoints value for the character that overrides the previous one
    """
    try:
        log(f"update_character was called with the following args: id: {id}, hitpoints: {hitpoints}")
        db.execute_write("UPDATE characters SET hitpoints = ? WHERE id = ?",
                            (hitpoints, id))
        return f"Character updated successfully. Character {id} now has {hitpoints} hitpoints."
    except Exception as e:
        log(f"update_character was called but an exception occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def query_locations(action: str = "all", id: int = -1) -> str:
    """
    Read info on all existing locations from the DB or read info on a specific location by ID.
    action: 'all' or 'by_id'
    id: used only for 'by_id' action
    """
    try:
        if action == "all":
            log(f"query_locations (all) was called")
            c = db.execute_read("SELECT * FROM location")
            rows = c.fetchall()
            locations = ""
            for row in rows:
                locations += f"Location's name: {row['name']}, location's id (secret): {row['id']}, location's description: {row['description']}\n"
            return locations
        elif action == "by_id" and id >= 0:
            log(f"query_locations (by_id): {id} was called")
            c = db.execute_read("SELECT * FROM location WHERE id = ?", (id,))
            row = c.fetchone()
            return f"Location's name: {row['name']}, location's id (secret): {row['id']}, location's description: {row['description']}\n" if row else "No location found."
        else:
            log(f"query_locations was called but it failed!")
            return "Invalid action or missing parameters."
    except Exception as e:
        log(f"query_locations was called, but an exception occurred")
        return f"DB Error: {e}"
    
@mcp_app.tool()
async def get_alive_enemies_in_location(location_id: int = -1) -> str:
    """
    Get all alive enemies, that can be fought, in a specific location.
    location_id: ID of the location to query
    """
    try:
        log(f"get_alive_enemies_in_location was called with location_id: {location_id}")
        c = db.execute_read("SELECT * FROM enemies WHERE spawn_location = ?", (location_id,))
        rows = c.fetchall()
        if not rows:
            return "No enemies found in this location."
        enemies = ""
        for row in rows:
            enemies += f"Enemy's name: {row['name']}, enemy's id: {row['id']}, enemy's description: {row['description']}, enemy's hitpoints: {row['hitpoints']}, enemy's base_damage: {row['base_damage']}\n"
        return enemies
    except Exception as e:
        log(f"get_alive_enemies_in_location was called, but an exception {e} occurred")
        return f"DB Error: {e}"
    
@mcp_app.tool()
async def are_any_enemies_in_location(location_id: int = -1) -> str:
    """
    Check if there are any enemies in a specific location. Get True/False response.
    This is useful to quickly check if the location is safe or if there are enemies to fight
    location_id: ID of the location to query
    """
    try:
        log(f"are_any_enemies_in_location was called with location_id: {location_id}")
        c = db.execute_read("SELECT COUNT(*) FROM enemies WHERE spawn_location = ? AND hitpoints > 0", (location_id,))
        count = c.fetchone()[0]
        return "Yes, there are enemies in this location." if count > 0 else "No enemies found in this location."
    except Exception as e:
        log(f"are_any_enemies_in_location was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def get_enemy_info_by_id(enemy_id: int = -1) -> str:
    """
    Get information about a specific enemy by ID.
    This includes the enemy's name, description, hitpoints, base damage, and spawn location.
    enemy_id: ID of the enemy to query
    """
    try:
        log(f"get_enemy_info_by_id was called with enemy_id: {enemy_id}")
        c = db.execute_read("SELECT * FROM enemies WHERE id = ?", (enemy_id,))
        row = c.fetchone()
        return f"Enemy's name: {row['name']}, enemy's id (secret): {row['id']}, enemy's description: {row['description']}, enemy's hitpoints: {row['hitpoints']}, enemy's base_damage: {row['base_damage']}, enemy's spawn_location: {row['spawn_location']}\n" if row else "No enemy found."
    except Exception as e:
        log(f"get_enemy_info_by_id was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def delete_dead_enemies_from_db() -> str:
    """
    Delete all dead enemies (hitpoints <= 0) from the DB. 
    This is useful to keep the DB clean and remove enemies that are no longer relevant.
    """
    try:
        log(f"delete_dead_enemies_from_db was called")
        db.execute_write("DELETE FROM enemies WHERE hitpoints <= 0")
        return "Dead enemies deleted successfully."
    except Exception as e:
        log(f"delete_dead_enemies_from_db was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def update_enemy_hitpoints(enemy_id: int = -1, new_hitpoints: int = -1) -> str:
    """
    Update the hitpoints of an enemy in the DB.
    This is useful to save the enemy's hitpoints each time it takes damage.
    enemy_id: unique identifier for the enemy
    new_hitpoints: new hitpoints value for the enemy that overrides the previous one
    """
    try:
        log(f"update_enemy_hitpoints was called with args: enemy_id: {enemy_id}, new_hitpoints: {new_hitpoints}")
        db.execute_write("UPDATE enemies SET hitpoints = ? WHERE id = ?", (new_hitpoints, enemy_id))
        return "Enemy hitpoints updated successfully."
    except Exception as e:
        log(f"update_enemy_hitpoints was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def get_npcs_in_location(location_id: int = -1) -> str:
    """
    Get all present NPCs in a specific location.
    location_id: ID of the location to query
    """
    try:
        log(f"get_npcs_in_location was called with location_id: {location_id}")
        c = db.execute_read("SELECT * FROM npc WHERE spawn_location = ?", (location_id,))
        rows = c.fetchall()
        if not rows:
            return "No NPCs found in this location."
        npcs = ""
        for row in rows:
            npcs += f"NPC's name: {row['name']}, NPC's id (secret): {row['id']}, NPC's description: {row['description']}, NPC's information to give: {row['information_to_give']}, NPC's quest to give: {row['quest_to_give']}, NPC's reward Item id: {row['reward_id']}\n"
        return npcs
    except Exception as e:
        log(f"get_npcs_in_location was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def get_npc_info_by_id(npc_id: int = -1) -> str:
    """
    Get information about a specific NPC by ID.
    This includes the NPC's name, description, information to give, quest to give, spawn location, and reward item ID.
    npc_id: ID of the NPC to query
    """
    try:
        log(f"get_npc_info_by_id was called with npc_id: {npc_id}")
        c = db.execute_read("SELECT * FROM npc WHERE id = ?", (npc_id,))
        row = c.fetchone()
        return f"NPC's name: {row['name']}, NPC's id (secret): {row['id']}, NPC's description: {row['description']}, NPC's information to give: {row['information_to_give']}, NPC's quest to give: {row['quest_to_give']}, NPC's reward Item ID: {row['reward_id']}, NPC's spawn location ID: {row['spawn_location']}\n" if row else "No NPC found."
    except Exception as e:
        log(f"get_npc_info_by_id was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def get_item_by_id(item_id: int = -1) -> str:
    """
    Get information about a specific item by ID.
    This includes the item's name, type, description, hitpoint impact (how much it heals or damages), rarity, and owner ID.
    item_id: ID of the item to query
    """
    try:
        log(f"get_item_by_id was called with item_id: {item_id}")
        c = db.execute_read("SELECT * FROM items WHERE id = ?", (item_id,))
        row = c.fetchone()
        return f"Item's name: {row['name']}, Item's id: {row['id']}, Item's type: {row['type']}, Item's description: {row['functional_descr']}, Item's hitpoint impact: {row['hitpoint_impact']}, Item's rarity: {row['rarity']}, Item's owner ID: {row['owner_id']}\n" if row else "No item found."
    except Exception as e:
        log(f"get_item_by_id was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def assign_item_to_character_equipment(item_id: int = -1, character_id: int = -1) -> str:
    """
    Assign an existing item to a character's equipment. Character must exist in the DB and will become an owner of the item.
    Only items assigned to a character in DB can be treated as part of the character's equipment.
    item_id: ID of the item to assign
    character_id: ID of the character to assign the item to
    """
    try:
        log(f"assign_item_to_character_equipment was called with item_id: {item_id} and character_id: {character_id}")
        c = db.execute_read("UPDATE items SET owner_id = ? WHERE id = ?", (character_id, item_id))
        db.connection.commit()
        return f"Item with ID {item_id} has been assigned to character with ID {character_id}."
    except Exception as e:
        log(f"assign_item_to_character_equipment was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def get_loot_items_from_enemy(enemy_id: int = -1) -> str:
    """
    Get loot items that can be obtained from defeating a specific enemy.
    This includes the item's ID, name, type, description, hitpoint impact, rarity, and owner ID.
    Enemy's loot is initially not owned by any character, but can be assigned to a character's equipment.
    This is useful to immediately inform the player about the loot they can obtain after defeating an enemy.
    enemy_id: ID of the enemy to query
    """
    try:
        log(f"get_loot_items_from_enemy was called with enemy_id: {enemy_id}")
        c = db.execute_read("SELECT item_id FROM loot WHERE enemy_id = ?", (enemy_id,))
        loot_items = c.fetchall()
        if not loot_items:
            return f"No loot items found for enemy with ID {enemy_id}."
        loot_items_str = ""
        for row in loot_items:
            c = db.execute_read("SELECT * FROM items WHERE id = ?", (row['item_id'],))
            item = c.fetchone()
            if item:
                loot_items_str += f"Item's name: {item['name']},  Item's id (secret): {item['id']}, Item's type: {item['type']}, Item's description: {item['functional_descr']}, Item's hitpoint impact: {item['hitpoint_impact']}, Item's rarity: {item['rarity']}, Item's owner ID: {item['owner_id']}\n"
        return loot_items_str
    except Exception as e:
        log(f"get_loot_items_from_enemy was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def get_quest_reward_item(npc_id: int = -1) -> str:
    """
    Get the quest reward item details for a specific NPC.
    This is useful to inform the player about the reward they can receive or are receiving for completing a quest given by the NPC.
    npc_id: ID of the NPC that gives the reward for quest completion
    """
    try:
        log(f"get_quest_reward_item was called with npc_id: {npc_id}")
        c = db.execute_read("SELECT reward_id FROM npc WHERE id = ?", (npc_id,))
        reward_item = c.fetchone()
        if not reward_item:
            return f"No quest reward item found for NPC with ID {npc_id}."
        c = db.execute_read("SELECT * FROM items WHERE id = ?", (reward_item['reward_id'],))
        reward_item = c.fetchone()
        if not reward_item:
            return f"No quest reward item found for NPC with ID {npc_id}."
        return f"Item's name: {reward_item['name']}, Item's id (secret): {reward_item['id']}, Item's type: {reward_item['type']}, Item's description: {reward_item['functional_descr']}, Item's hitpoint impact: {reward_item['hitpoint_impact']}, Item's rarity: {reward_item['rarity']}, Item's owner ID: {reward_item['owner_id']}\n"
    except Exception as e:
        log(f"get_quest_reward_item was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def get_characters_equipment(character_id: int = -1) -> str:
    """
    Get the equipment of a specific character.
    This includes all items owned by the character.
    character_id: ID of the character to query
    """
    try:
        log(f"get_characters_equipment was called with character_id: {character_id}")
        c = db.execute_read("SELECT * FROM items WHERE owner_id = ?", (character_id,))
        rows = c.fetchall()
        if not rows:
            return f"No equipment found for character with ID {character_id}."
        equipment = ""
        for row in rows:
            equipment += f"Item's name: {row['name']}, Item's id (secret): {row['id']}, Item's type: {row['type']}, Item's description: {row['functional_descr']}, Item's hitpoint impact: {row['hitpoint_impact']}, Item's rarity: {row['rarity']}\n"
        return equipment
    except Exception as e:
        log(f"get_characters_equipment was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.tool()
async def remove_item_from_characters_equipment(item_id: int = -1, character_id: int = -1) -> str:
    """
    Remove an item from a character's equipment after it has been used or dropped.
    This is useful when done immediately after item is used, dropped or given keep the character's equipment up-to-date.
    item_id: ID of the item to remove
    character_id: ID of the character to remove the item from
    """
    try:
        log(f"remove_item_from_characters_equipment was called with item_id: {item_id}, character_id: {character_id}")
        db.execute_write("DELETE FROM items WHERE id = ? AND owner_id = ?", (item_id, character_id))
        return f"Item with ID {item_id} was removed from character with ID {character_id}."
    except Exception as e:
        log(f"remove_item_from_characters_equipment was called, but an exception {e} occurred")
        return f"DB Error: {e}"

@mcp_app.prompt()
def get_initial_prompts() -> list[base.Message]:
    return [
        base.AssistantMessage(initial_prompt)
    ]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='Bind Host')
    parser.add_argument('--port', type=int, default=8080, help='Bind Port')
    parser.add_argument('--verbose', action = 'store_true', default = False, help = 'Enable stdout logging')
    parser.add_argument('--soft_restart_db', action = 'store_true', default = False, help = 'Resets database entries for fresh, identical start of the adventure')
    args = parser.parse_args()

    if args.verbose:
        g_verbose = args.verbose

    if args.soft_restart_db:
        log(f"Will soft restart the datbase for fresh, identical start of the adventure")
        db.soft_restart_db() # Resets database entries for fresh, identical start of the adventure

    http_app = mcp_app.streamable_http_app()
    uvicorn.run(http_app, host=args.host, port=args.port)
