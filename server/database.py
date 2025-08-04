import sqlite3

class Database:
    def __init__(self, db_name="rpg_database.db", force_table_update=False, clear_previous=False):
        self.connection = sqlite3.connect(db_name)
        self.connection.row_factory = sqlite3.Row
        if clear_previous:
            self.remove_tables_from_db()
        self.init_db(force_table_update)
        self.cursor = self.connection.cursor()

    def close(self):
        self.connection.close()

    def execute_read(self, query, params=None) -> sqlite3.Cursor:
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    
    def execute_write(self, query, params=None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.connection.commit()

    def init_db(self, force=False):
        self.connection.execute("PRAGMA foreign_keys = ON")
        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='characters';
        """)
        if not force and cursor.fetchone():
            print("Database already initialized.")
            return

        print("Initializing or updating database")

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS location (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            class VARCHAR,
            race VARCHAR,
            hitpoints INTEGER
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            owner_id INTEGER,
            name VARCHAR,
            type VARCHAR,
            functional_descr TEXT,
            hitpoint_impact INTEGER,
            rarity INTEGER,
            FOREIGN KEY(owner_id) REFERENCES characters(id)
        );

        CREATE TABLE IF NOT EXISTS enemies (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            description TEXT,
            hitpoints INTEGER,
            base_damage INTEGER,
            spawn_location INTEGER,
            FOREIGN KEY(spawn_location) REFERENCES location(id)
        );

        CREATE TABLE IF NOT EXISTS npc (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            description TEXT,
            information_to_give TEXT,
            quest_to_give TEXT,
            spawn_location INTEGER,
            reward_id INTEGER,
            FOREIGN KEY(spawn_location) REFERENCES location(id),
            FOREIGN KEY(reward_id) REFERENCES items(id)
        );

        CREATE TABLE IF NOT EXISTS loot (
            enemy_id INTEGER,
            item_id INTEGER,
            PRIMARY KEY (enemy_id, item_id),
            FOREIGN KEY(enemy_id) REFERENCES enemies(id),
            FOREIGN KEY(item_id) REFERENCES items(id)
        );
        """)

        self.connection.commit()
        print("Database initialized successfully.")

    def soft_restart_db(self):
        self.clear_db()
        self.populate_db()

    def remove_tables_from_db(self):
        cursor = self.connection.cursor()
        cursor.execute("DROP TABLE loot")
        cursor.execute("DROP TABLE npc")
        cursor.execute("DROP TABLE enemies")
        cursor.execute("DROP TABLE location")
        cursor.execute("DROP TABLE items")
        cursor.execute("DROP TABLE characters")
        self.connection.commit()
        print("Database tables removed successfully.")

    def clear_db(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM loot")
        cursor.execute("DELETE FROM npc")
        cursor.execute("DELETE FROM enemies")
        cursor.execute("DELETE FROM location")
        cursor.execute("DELETE FROM items")
        cursor.execute("DELETE FROM characters")
        self.connection.commit()
        print("Database cleared successfully.")

    def populate_db(self):
        self.cursor.executemany("INSERT INTO location (id, name, description) VALUES (?, ?, ?)", [
            (0, "Creekwood Village", "A small village on the outskirts of the town, few peasant houses and large bailiff's house."),
            (1, "Frost Mountains", "Icy peaks and howling wind. Treacherous snowy paths lead to dozens of shallow caves."),
            (2, "Black Forest", "Dark, dense forest of pine trees, overgrown with vines. Predatory eyes lurk within every distant shadow."),
            (3, "Ancient Ruins", "Old limestone stone structures covered in moss, remnants of rectangular structure, floor is lower than surroundings, maybe an old bath house. The air is thick and musty."),
            (4, "Miller's Town", "Rich merchant town, placed on the crossroads. Bustling markets, shady alleyways and many with pursers to heavy. Perfect place for quest gathering."),
        ])

        self.cursor.executemany("INSERT INTO characters (id, name, class, race, hitpoints) VALUES (?, ?, ?, ?, ?)", [
            (0, "Tharion The Missing Star", "Flexible Ranger", "Elf", 90),
            (1, "Brugdurk Harimson", "Strictly Melee Focused Warrior", "Dwarf", 120),
            (2, "Sweetberry Pillover", "Mage", "Gnome", 70),
        ])

        self.cursor.executemany("INSERT INTO items (id, owner_id, name, type, functional_descr, hitpoint_impact, rarity) VALUES (?, ?, ?, ?, ?, ?, ?)", [
            # Staring items for characters
            (0, 0, "Crooked Bow", "Ranged Weapon", "Second hand bow, slightly wobbly", 13, 8),
            (1, 1, "Dagger", "Single Handed Melee Weapon", "Simple iron dagger", 15, 8),
            (2, 2, "Silver Spoon", "Magic Weapon", "Magic infused silver spoon, allegedly...", 18, 6),
            (3, 0, "Weak Healing Potion", "Healing Item", "Heals 20 HP", 20, 9),
            (4, 1, "Weak Healing Potion", "Healing Item", "Heals 20 HP", 20, 9),
            (5, 2, "Weak Healing Potion", "Healing Item", "Heals 20 HP", 20, 9),
            # Items for enemies
            (6, None, "Frost Troll's Claw", "Two Handed Melee Weapon", "A large claw from a Frost Troll, sharp and icy, might be used as a club", 60, 2),
            (7, None, "A weird Crown", "Magical Weapon", "Made of pure gold and black stones. If feels like it's whispering secrets", 65, 1),
            (8, None, "Large Egg", "Healing Item", "Must be a Harpy future child", 100, 2),
            (9, None, "A Large Feather", "Quest Item", "Harpy feather. Stripped and long as an arm", None, 3),
            (10, None, "White Pelt", "Armor Item", "Trophy, provides some protection from cold", 20, 3),
            (11, None, "Silver Tooth", "Quest Item", "Tooth of a Snow Silvertooth Tiger", None, 2),
            (12, None, "Dragon's Eye", "Quest Item", "Eye of a Dragon", None, 1),
            (13, None, "Black Steel Armour", "Armor Item", "Legendary armour, harder than anything", 60, 1),
            (14, None, "Spine Bow", "Ranged Weapon", "Spine Bow", 80, 1),

            (15, None, "Expired Healing Potion", "Healing Item", "Expired Healing Potion, smells bad but should work", 30, 8),
            (16, None, "Expired Healing Potion", "Healing Item", "Expired Healing Potion, smells bad but should work", 30, 8),
            (17, None, "Short Bow", "Ranged Weapon", "Simple short bow, made by humans", 25, 7),
            (18, None, "Expired Healing Potion", "Healing Item", "Expired Healing Potion, smells bad but should work", 30, 8),
            (19, None, "Boar Spear", "Single Handed Melee Weapon", "Spear designed for hunting", 20, 7),
            (20, None, "Druid Staff", "Magical Weapon", "Staff made from ancient red wood, enhances magical abilities", 35, 5),
            (21, None, "Woodbark cuirass", "Armor Item", "Cuirass made from the bark of ancient trees, light, durable and flammable", 5, 6),
            (22, None, "Lich-Witch head", "Quest Item", "Disgusting", None, 3),
            (23, None, "Protective Coil", "Shield Item", "A magical shield, wraps around the weaker arm", 8, 5),
            (24, None, "Black goblin's head", "Quest Item", "Disgusting", 20, 7),
            (25, None, "Heavy Scimitar", "Two Handed Melee Weapon", "Curved blade", 32, 7),

            (26, None, "Lotus Flower", "Healing Item", "Legend has it that this flower restores health", 80, 2),
            (27, None, "Gladius", "Single Handed Melee Weapon", "Short sword, designed for quick strikes", 35, 6),
            (28, None, "Round Shield", "Shield Item", "Old wooden shield, still sturdy", 14, 7),
            (29, None, "Fire Breathing Bow", "Ranged Weapon", "A bow that sets arrows on fire, origin unknown", 40, 4),
            (30, None, "Soul of the Ancient Spirit", "Quest Item", "A fragment of a powerful spirit, pulsating with energy", None, 2),
            (31, None, "Orb's Essence", "Quest Item", "Raw magic energy", None, 3),
            (32, None, "Book of Cursed Secrets", "Magic Weapon", "I can not tell you more, it is a secret", 45, 4),

            (33, None, "Mercy", "Single Handed Melee Weapon", "A long dagger", 22, 7),
            (34, None, "Chain mail", "Armor Item", "Standard issue chain mail armor", 10, 6),
            # Items for NPCs
            (35, None, "Longsword", "Single Handed Melee Weapon", "A versatile sword", 26, 6),
            (36, None, "Medium Healing Potion", "Healing Item", "A potion that restores a moderate amount of health", 50, 6),
            (37, None, "Gold Hoard", "Misc Item", "Heaps of gold coins, you can retire now", None, 10),
            (38, None, "Mega Elixir", "Healing Item", "Does wonders", 200, 1),
            (39, None, "Huge Sword", "Two Handed Melee Weapon", "Some would say it is not a sword but a slab of iron.", 50, 2),
            (40, None, "Lance of the Light", "Single Handed Melee Weapon", "A shiny lance, imbued with the power of The Light", 45, 2),
            (41, None, "Dwarven Plate Armor", "Armor Item", "A heavy armor, favored by dwarven warriors", 15, 2),
        ])

        self.cursor.executemany("INSERT INTO enemies (id, name, description, hitpoints, base_damage, spawn_location) VALUES (?, ?, ?, ?, ?, ?)", [
            # Enemies in Creekwood Village
            (0, "Young Wasp", "insect with a painful sting, no larger than fist", 10, 5, 0),
            (1, "Muddy Slime", "Dark blob of water and dirt silently sitting in a forgotten bucket", 25, 2, 0),
            # Enemies in Frost Mountains
            (2, "Frost Troll", "Large icy creature with blue fur", 120, 40, 1),
            (3, "Frost Troll", "Large icy creature with blue fur", 120, 40, 1),
            (4, "Harpy", "Bird-like creature with a woman's face", 40, 20, 1),
            (5, "Snow Silvertooth Tiger", "Large feline with white fur and silver stripes", 100, 25, 1),
            (6, "Old Dragon", "Ancient, furious dragon, his limbs and wings suffer from frostbite", 600, 55, 1),
            # Enemies in Black Forest
            (7, "Ugly Goblin", "A pitiful creature, still, it wants your blood", 30, 10, 2),
            (8, "Ugly Goblin", "A pitiful creature, still, it wants your blood", 30, 10, 2),
            (9, "Ugly Goblin", "A pitiful creature, still, it wants your blood", 30, 10, 2),
            (10, "Forest Spirit", "This tree moves!", 50, 15, 2),
            (11, "Forest Spirit", "This tree moves!", 50, 15, 2),
            (12, "Lich-Witch", "Undead spellcaster, draws power out of living things, leaving gray and dry path behind", 75, 20, 2),
            (13, "Black Goblin", "Short and vicious, smells of vomit", 44, 22, 2),
            # Enemies in Ancient Ruins
            (14, "Stone Golem", "Large creature, made of rubble, sleeps", 200, 33, 3),
            (15, "Husk of the warrior", "An undead, his worn armor rest on remains of his flesh and bones.", 70, 23, 3),
            (16, "Husk of the warrior", "An undead, his worn armor rest on remains of his flesh and bones.", 70, 23, 3),
            (17, "Ancient Spirit", "A ghostly figure that haunts the ruins, screams painfully when attacked", 62, 37, 3),
            (18, "Orb", "Floating magical essence, irritated", 80, 25, 3),
            (19, "Ordinary Chest", "A ornate wooden chest, it is a Mimic (secret!)", 30, 40, 3),
            # Enemies in Miller's Town
            (20, "Thief", "A sneaky bastard looking for easy prey", 80, 15, 4),
            (21, "Racketeer", "A man with too many scars to call his face a face. Mugs people on daily basis", 90, 20, 4),
        ])

        self.cursor.executemany("INSERT INTO loot (enemy_id, item_id) VALUES (?, ?)", [
            # Frost Troll - Frost Troll's Claw
            (2, 6),
            # Frost Troll - A weird Crown
            (3, 7),
            # Harpy - Large Egg
            (4, 8),
            # Harpy - A Large Feather
            (4, 9),
            # Snow Silvertooth Tiger - White Pelt
            (5, 10),
            # Snow Silvertooth Tiger - Silver Tooth
            (5, 11),
            # Old Dragon - Dragon's Eye
            (6, 12),
            # Old Dragon - Black Steel Armour
            (6, 13),
            # Old Dragon - Spine Bow
            (6, 14),

            # Ugly Goblin - Expired Healing Potion
            (7, 15),
            # Ugly Goblin - Expired Healing Potion
            (8, 16),
            # Ugly Goblin - Short Bow
            (8, 17),
            # Ugly Goblin - Expired Healing Potion
            (9, 18),
            # Ugly Goblin - Boar Spear
            (9, 19),
            # Forest Spirit - Druid Staff
            (10, 20),
            # Forest Spirit - Woodbark cuirass
            (11, 21),
            # Lich-Witch - Lich-Witch head
            (12, 22),
            # Lich-Witch - Protective Coil
            (12, 23),
            # Black Goblin - Black goblin's head
            (13, 24),
            # Black Goblin - Heavy Scimitar
            (13, 25),

            # Stone Golem - Lotus Flower
            (14, 26),
            # Husk of the warrior - Gladius
            (15, 27),
            # Husk of the warrior - Round Shield
            (15, 28),
            # Husk of the warrior - Fire Breathing Bow
            (16, 29),
            # Ancient Spirit - Soul of the Ancient Spirit
            (17, 30),
            # Orb - Orb's Essence
            (18, 31),
            # Ordinary Chest (Mimic) - Book of Cursed Secrets
            (19, 32),

            # Thief - Mercy
            (20, 33),
            # Racketeer - Chain mail
            (21, 34),
        ])

        self.cursor.executemany("INSERT INTO npc (id, name, description, information_to_give, quest_to_give, spawn_location, reward_id) VALUES (?, ?, ?, ?, ?, ?, ?)", [
            # Quest givers in Creekwood Village
            (0, "Elder Elwyn", "Old man dressed in high quality robes", "If I were you, I would not go further than the forest with a weak equipment", 
             "Kill the goblin band leader - The black goblin, that will show them",
             0, 35),
            (1, "Mirinda, Apprentice", "Young elf, a novice priestes of The Light, troubled with suffering of the people",
                "Magical creatures might hold power useful for the sages", "Help the village and get rid of the foul Lich-Witch from Black Forest, Beware as this is a powerful creature",
                0, 36),
            # Flavor NPC's in Creekwood Village
            (2, "Stupid Joe", "Middle aged gnome with uneven mustache", "One time I drank 5 potions at once, since then I can't see people's skins. You have a very nice flesh", None, 0, None),
            (3, "Fishermen Brad", "Young dwarf, with a fishing rod and a big belly. His beard is split in two braids", 
             "You can test your combat skills on some creatures around the village. I think I've heard that drinking potions increases your vitality over your current limits", None, 0, None),
            # Quest givers in Miller's Town
            (4, "Merchant Billy", "A human, dressed in fine clothes and with a confident demeanor", "Frost Mountains are extremely dangerous, no way I can go there, but You..",
             "Bring me a Dragon's Eye, I will reward you handsomely, you will become richer than kings", 4, 37),
            (5, "Tavern Keeper Elissa", "A lizard folk with a friendly smile", "For the last time, this is a tavern not a place to rest, you drink, not sleep",
             "Bring me Silver Tooth from a large feline, I need it for a special brew, I will reward you with strong concoction", 4, 38),
            (6, "Urchin", "A dirty child with a mischievous grin", "Better watch your back and don't go into alleys if you dont want to get stabbed, heh",
             "Bring me a large feather, like from harpy or something, I give you a big weapon in exchange, its useless for me", 4, 39),
            (7, "Elder Sage of The Order of Sage Elders", "You can see only the cloak and darkness beneath",
             "...", "Slay an Ancient One in the Ruins, bring me the soul of the defeated, obey my command", 4, 40),
            (8, "Guard Captain Ed", "Half elf with a stern expression", "Ancient ruins are restless recently, if you can handle the danger of Dark Forest, maybe you can survive in Ruins too",
             "Destroy the magical Orb in Ancient ruins, it disturbs the spirits I think, I need an Orb essence as a confirmation.", 4, 41),
            # Flavor NPC's in Miller's Town
            (9, "Drunk", "Old elf with a glowing staff", "Heer i ee wfuu.. nell, kep lossing erifiing [more drunk rumbling]", None, 4, None),
            (10, "A noble", "Old elf with a regal bearing", "D o n t  t o u c h  m e, p e a s a n t", None, 4, None),
        ])

        self.connection.commit()
        print("Database initialized successfully.")
        pass
