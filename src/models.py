class Item:
    def __init__(self, name):
        self.name = name
        self.attributes = {}

    def to_dict(self):
        return {
            "Name": self.name,
            **self.attributes
        }

class Weapon(Item):
    FIELDS = [
        "Name",  
        "Type",
        "Damage",
        "Delay", 
        "Stats",
        "Classes",
        "Races",
        "Effect",
        "WT",
        "Size",
        "Slot",
        "Magic Item",
        "Lore Item",
        "No Drop",
        "30d Avg",
        "90d Avg",
        "All Time Avg"
    ]

class Equipment(Item):
    FIELDS = [
        "Name",  
        "Type",
        "Slot",
        "AC",
        "Stats", 
        "Classes",
        "Races",
        "Effect",
        "WT",
        "Size",
        "Magic Item",
        "Lore Item",
        "No Drop",
        "30d Avg",
        "90d Avg",
        "All Time Avg"
    ]