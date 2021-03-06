from math import sqrt
from Tile import is_blocked
import tcod as libtcod
import field_of_view
import constants
import random
import utils
import textwrap


class Object(object):

	def __init__(self, x, y, img, name, blocks=False, block_sight=None, fighter=None, ai=None, item=None, container=None, initial_light_radius=0, damage_at_impact=0):
		self.x = x
		self.y = y
		self.img = constants.tiles[img]
		self.name = name
		self.blocks = blocks
		self.fighter = fighter
		self.ai = ai
		self.item = item
		self.container = container
		self.block_sight = block_sight
		self.sent_messages = []
		self.noise_made = {'range': 0, 'chance_to_be_heard': 0, 'source': '', 'sound_name': ''} 
		self.heard_noises = []
		self.noises = {'move': (70, 8), 'crouch': (10, 4)} # CHANCE | RANGE
		self.sounds = {'sound_walk': '', 'sound_sneak': ''} # names of sounds
		self.initial_light_radius = initial_light_radius # player is a light source variable for objects
		self.damage_at_impact = damage_at_impact
		self.description =  '' # add multiple entries in dict

		if self.fighter:
			self.fov_map = []
			self.fov_map = field_of_view.set_fov(self.fov_map)
			self.fighter.owner = self

		if self.ai:
			self.ai.owner = self

		if self.item:
			self.item.owner = self

		if self.container:
			self.container.owner = self

	def move(self, dx, dy, _map, fov_map, objects, pushing=False):
		if not is_blocked(self.x + dx, self.y + dy, _map, objects) and (self.fighter is not None):#or pushing):
			self.clear(self.x, self.y, _map)
			self.x += dx
			self.y += dy
			if not self.fighter.sneaking:
				# make this into a function
				# source = self
				# sum modificators from armour
				self.noise_made['range'] = self.noises['move'][1]
				self.noise_made['chance_to_be_heard'] = self.noises['move'][0] # + armor
				self.noise_made['source'] = self
				self.noise_made['sound_name'] = self.sounds['sound_walk']
			else:
				self.noise_made['range'] = self.noises['crouch'][1]
				self.noise_made['chance_to_be_heard'] = self.noises['crouch'][0]
				self.noise_made['source'] = self
				self.noise_made['sound_name'] = self.sounds['sound_sneak']
		else:
			for obj in objects:
				# add noises of battle
				if self.name != constants.PLAYER_NAME:
					if (self.x + dx == obj.x and self.y + dy == obj.y) and obj.fighter is not None and self.fighter is not None and obj.name == constants.PLAYER_NAME:
						self.fighter.attack(obj)
				else:
					if (self.x + dx == obj.x and self.y + dy == obj.y) and obj.fighter is not None and self.fighter is not None:
						self.fighter.attack(obj)

	def draw(self, screen):
		_x = self.x * constants.TILE_SIZE
		_y = self.y * constants.TILE_SIZE

		screen.blit(self.img, (_x, _y))

	def clear(self, x, y, _map):
		_map[x][y].block_sight = False

	def distance_to(self, other):
		dx = other.x - self.x
		dy = other.y - self.y
		return sqrt(dx ** 2 + dy ** 2)

	def clear_messages(self):
		self.sent_messages = []

	def send_message(self):
		# add the possibility to change the color (it would need to be a list of message and the RGB value)
		pass

	def destroy(self): # make it that it removes obj from objects
		self.item = None
		self.img = None

	def send_message(self, message):

		if len(message) > 56:
			message_to_wrap = textwrap.wrap(message, 56)

			for wrapped_message in message_to_wrap:
				self.sent_messages.append(wrapped_message)

		else:
			self.sent_messages.append(message)

class Fighter(object):

	# every being makes noise and can attack, have inventory
	def __init__(self, hp, initial_attack_stat, initial_defense_stat, special_attack_fn=None, class_type=None): # make it not that straightforward, add chances to stun, chances to miss etc.
		self.starting_max_hp = hp
		self.hp = hp
		self.initial_attack_stat = initial_attack_stat
		self.initial_defense_stat = initial_defense_stat
		self.inventory = []
		self.equipment = []
		self.effects = []
		self.sneaking = False
		self.knees = 10 # knee health
		# add modificators like hearing and chance depending on armor
		self.modificators = {}

		# Modificators will be values that can add, or subtract from chances.

	@property
	def max_light_radius(self):

		bonus_light = 0

		for eq in self.equipment:
			if eq.item.equipment.light_radius_bonus is not None:
				if eq.item.equipment.activated:
					# It activates here, the Equipment object has the values already "on"
					bonus_light += eq.item.equipment.light_radius_bonus

		return self.owner.initial_light_radius + bonus_light

	@property
	def attack_stat(self):
		final_val = 0
		for piece in self.equipment:
			final_val += piece.item.equipment.power_bonus
		return final_val

	@property
	def max_hp(self):
		bonus = 0
		for piece in self.equipment:
			bonus += piece.item.equipment.max_health_bonus
		return self.starting_max_hp + bonus

	@property
	def defense_stat(self):
		bonus = 0
		for piece in self.equipment:
			bonus += piece.item.equipment.defence_bonus
		return self.initial_attack_stat + bonus

	@property
	def burden(self): # if weight will be too high, player will scream | items worn are 1.3 times heavier | Add calculations that decrease weight depending on player's strength

		val = 0

		for piece in self.equipment:
			val += piece.item.weight * 1.3

		for piece in self.inventory:
			val += piece.item.weight

		return val

	@property
	def armor_to_be_heard_modificator(self):
		bonus_chance = 0
		for piece in self.equipment:
			bonus_chance += piece.item.equipment.chance_to_be_heard_modificator # make this as an argument to an generic function - "add to a modificator"

		return bonus_chance

	@property
	def armor_to_be_seen_modificator(self):
		bonus_chance = 0
		for piece in self.equipment:
			bonus_chance += piece.item.equipment.chance_to_be_seen_modificator

		return bonus_chance

	@property
	def armor_to_see_modificator(self):
		bonus_chance = 0
		for piece in self.equipment:
			bonus_chance += piece.item.equipment.chance_to_see_modificator

		return bonus_chance

	@property
	def armor_to_hear_modificator(self):
		bonus_chance = 0
		for piece in self.equipment:
			bonus_chance += piece.item.equipment.chance_to_hear_modificator

		return bonus_chance

	#@property
	#def modificator_bonus(self, mod_name):
	#	for effect in self.effects
	#		if effect.modificator == mod_name:
	#			return effect.modificator


	def attack(self, target):

		#make miss a random chance, not 0 - if it stays that way, even the most of the powerful creatures will deal 1 damage

		attack_value = random.randint(((self.initial_attack_stat + self.attack_stat) - random.randint(1, self.initial_attack_stat)), self.initial_attack_stat + self.attack_stat) + random.randint(0, self.initial_attack_stat) # miss cannot be included in damage, if damage == 0 -> "but does no damage"

		attack_value = attack_value - (target.fighter.defense_stat / 2)

		miss = random.randint(0, 100) < 3 # miss chance 

		if not miss:

			if attack_value > 0:
				target.fighter.hp -= attack_value
				mess = "{0} attacks {1} and deals {2} dmg!".format(self.owner.name.title(), target.name.title(), attack_value)
			else:
				mess = "{0} attack bounces off.".format(self.owner.name.title())
		else:
			mess = "{0} attacks {1} and misses!".format(self.owner.name.title(), target.name.title())

		self.owner.send_message(mess)

	def kill(self, fov_map, player_x, player_y, _map, images, player_light_radius):
		self.owner.ai = None
		self.owner.fighter = None
		self.owner.block_sight = False
		self.owner.blocks = False
		self.owner.img = images[6] # instead, use specific image for every character and corpse stats overall
		self.owner.noise_map = None
		self.owner.noises = None
		self.owner.sounds = None
		self.owner.clear(self.owner.x, self.owner.y, _map)
		field_of_view.fov_recalculate(fov_map, player_x, player_y, _map, radius=player_light_radius)
		self.owner.send_message(self.owner.name.title() + " is dead.")

	def get(self, objects, ui):
		for obj in objects:
			if obj.container is None:
				if obj.item is not None:
					if self.owner.x == obj.x and self.owner.y == obj.y:
						self.inventory.append(obj)
						self.owner.send_message("{0} picks up {1}.".format(self.owner.name.title(), obj.name.title()))
						objects.remove(obj)
						return obj
			else:
				if self.owner.x == obj.x and self.owner.y == obj.y:
					self.open(obj, ui, self)
					return obj

	def drop(self, objects, obj, ui):

		for ob in objects:
			if (ob.x, ob.y) == (self.owner.x, self.owner.y) and ob.name != constants.PLAYER_NAME:
				if ob.container is not None:
					ob.container.put_inside(obj)
					ui.remove_item_from_UI(obj.x, obj.y)
					self.inventory.remove(obj)
					self.owner.send_message("{0} puts {1} in {2}.".format(self.owner.name.title(), obj.name.title(), ob.name.title()))
					return
				else:
					self.owner.send_message("There is something already there.")
					return

		obj.x = self.owner.x
		obj.y = self.owner.y
		self.inventory.remove(obj)
		self.owner.send_message("{0} drops {1}.".format(self.owner.name.title(), obj.name.title()))
		objects.append(obj)

	def manage_fighter(self): # change to manage fighter, so that it deals with sneaking too
		for eq in self.equipment:
			if eq.item.equipment.activation_func is not None:
				eq.item.equipment.wear_off(self.owner, eq.name)

		if self.is_overburdened():
			self.knees = -0.1

		#for effect in self.effects:
		#	effect.update()

	def sneak(self):
		if not self.sneaking:
			self.sneaking = True
			self.owner.send_message("You crouch.")
		else:
			self.sneaking = False
			self.owner.send_message("You stand up.")

	def is_overburdened(self):
		return self.burden > 50 # some number

	def is_burdened(self):
		return self.burden > 40

	def open(self, obj, ui, user):
		if len(obj.container.loot) > 0: 
			obj.container.open(ui, user)
			self.owner.send_message("You open {0}.".format(obj.name.title()))
		else:
			self.owner.send_message("{0} is empty.".format(obj.name.title()))


class FSM(object):
	def __init__(self):
		self.active_state = None # method

	def update(self, **kwargs): # here add additional abilities
		if self.active_state is not None:
			self.active_state(**kwargs)

	def set_state(self, state):
		self.active_state = state


class SimpleAI(object):

	# simple ai does not make any noise nor listens for it
	def take_turn(self, _map, fov_map, objects, player):

		if fov_map[self.owner.x][self.owner.y] != 1: 
			# walk randomly
			rand_dir_x = random.randint(-1, 1)
			rand_dir_y = random.randint(-1, 1)

			self.owner.move(rand_dir_x, rand_dir_y, _map, fov_map, objects)

		else:
			# get to the player
			self.owner.name

			distance = self.owner.distance_to(player)

			if distance != 0:
			
				dx = player.x - self.owner.x
				dy = player.y - self.owner.y

				dx = int(round(dx / distance))
				dy = int(round(dy / distance))

				self.owner.move(dx, dy, _map, fov_map, objects)

class NoiseAI(object): # Maybe do something like this is base ai? and make components like CAN_USE_ITEMS, CAN_USE_MAGIC

	def __init__(self, brain):
		self.brain = brain
		self.brain.active_state = self.wander
		self.close_destination = False
		self.destination = None
		self.path = None
		self.player_out_of_sight = 0

	def take_turn(self, _map, objects, player, fov_map):
		# self.brain.active_state.__name__, self.owner.name
		# self.destination, self.owner.name
		self.brain.update(map=_map, objects=objects, player=player, fov_map=fov_map)

	def wander(self, **kwargs):

		_map = kwargs.get('map')
		fov_map = kwargs.get('fov_map')
		objects = kwargs.get('objects')
		player = kwargs.get('player')

		if not self.saw_player(fov_map, player):

			if self.destination is not None:
				path = self.set_path(_map, objects, self.destination, player)
				if not libtcod.path_is_empty(path[0]) and libtcod.path_size(path[0]) < 25:
					# self.destination
					self.brain.active_state = self.investigate
					self.path = path

			rand_dir_x = random.randint(-1, 1)
			rand_dir_y = random.randint(-1, 1)
			self.owner.move(rand_dir_x, rand_dir_y, _map, fov_map, objects)
			self.destination = None
				
		else:
			self.brain.active_state = self.chase


	def investigate(self, **kwargs):#fov_map, _map, objects, goal, player):
		# don't go anywhere until you don't reach goal
		_map = kwargs.get('map')
		fov_map = kwargs.get('fov_map')
		objects = kwargs.get('objects')
		player = kwargs.get('player')

		process = self.move_astar(self.path[0], _map, self.path[1], objects, self.path[2])

		if not self.saw_player(fov_map, player):

			# self.owner.x, self.owner.y, self.path[2]

			if process == 'reached':
				self.brain.active_state = self.wander
				self.destination = None

		else:
			self.brain.active_state = self.chase

		
	def set_path(self, _map, objects, goal, player):

		fov = libtcod.map_new(constants.MAP_WIDTH, constants.MAP_HEIGHT)

		for y1 in range(constants.MAP_WIDTH):
			for x1 in range(constants.MAP_HEIGHT):
				libtcod.map_set_properties(fov, x1, y1, not _map[x1][y1].block_sight, not _map[x1][y1].block_movement)

		for obj in objects:
			if obj.blocks and obj != self.owner and obj != player:
				libtcod.map_set_properties(fov, obj.x, obj.y, True, False)

		monster_path = libtcod.path_new_using_map(fov, 1.41)
		libtcod.path_compute(monster_path, self.owner.x, self.owner.y, goal[0], goal[1])
		return monster_path, fov, goal

	def move_astar(self, monster_path, _map, fov, objects, goal):
		x, y = libtcod.path_walk(monster_path, True)

		if x or y:
			# here will be time to move or attack, and it will return found and fighting

			self.move_to_target(_map, fov, objects, x, y) 

			if utils.non_obj_distance_to((goal[0], goal[1]), self.owner.x, self.owner.y) < 2:
				return 'reached'

	def chase(self, **kwargs): #_map, fov_map, objects, target_x, target_y):
		_map = kwargs.get('map')
		fov_map = kwargs.get('fov_map')
		objects = kwargs.get('objects')
		player = kwargs.get('player')
		
		# here implement losing player
		path = self.set_path(_map, objects, (player.x, player.y), player)
		progress = self.move_astar(path[0], _map, path[1], objects, (player.x, player.y))


	def move_to_target(self, _map, fov_map, objects, target_x, target_y):
		distance = utils.non_obj_distance_to((target_x, target_y), self.owner.x, self.owner.y)

		if distance != 0:
			# 'moving'
			
			dx = target_x - self.owner.x
			dy = target_y - self.owner.y

			dx = int(round(dx / distance))
			dy = int(round(dy / distance))

			self.owner.move(dx, dy, _map, fov_map, objects)	

	def saw_player(self, fov_map, player):

		if fov_map[self.owner.x][self.owner.y] != 1:
			return False

		if utils.can_see(player.fighter.modificators["mod_to_be_seen"] + player.fighter.armor_to_be_seen_modificator, self.owner.fighter.modificators["mod_to_seeing"]) + self.owner.fighter.armor_to_see_modificator:
			return True

class ConfusedAI(object):
	def __init__(self, brain):
		self.brain = brain
		self.duration = 6
		self.brain.active_state = self.tumble_around

	def take_turn(self, _map, objects, player, fov_map):
		self.brain.update(map=_map, objects=objects, player=player, fov_map=fov_map)

	def tumble_around(self, **kwargs):

		_map = kwargs.get('map')
		fov_map = kwargs.get('fov_map')
		objects = kwargs.get('objects')
		player = kwargs.get('player')

		rand_dir_x = random.randint(-1, 1)
		rand_dir_y = random.randint(-1, 1)
		self.owner.move(rand_dir_x, rand_dir_y, _map, fov_map, objects)
		self.owner.fighter.hp -= random.randint(1, 6)

		self.duration -= 1

		if self.duration <= 0:
			if self.owner != player:
				self.owner.ai = self.previous_ai
			else:
				self.owner.ai.brain = None
				self.owner.ai = None


class Item(object):
	def __init__(self, use_func=None, equipment=None, can_break=False, targetable=False, weight=0, effect=None, **kwargs):
		self.use_func = use_func
		self.can_break = can_break
		self.targetable = targetable
		self.equipment = equipment
		self.kwargs = kwargs
		self.weight = weight

		if self.equipment:
			self.equipment.owner = self

	def use(self, **kwargs): # throwing makes noise within throw function
		# it must be generic

		user = kwargs.get('user')
		ui = kwargs.get('UI')

		# str(user.name) + ": USER"

		kwargs.update(self.kwargs)

		if self.use_func is not None:

			if self.use_func(**kwargs) == 'used':
				# remove from obj inventory
				if user.fighter.hp > 0:
					ui.remove_item_from_UI(self.owner.x, self.owner.y)
					try:
						user.fighter.inventory.remove(self.owner)
					except ValueError:
						pass # it already has been removed 
			else:
				return 'cancelled'
		else:
			user.send_message("You cannot use that.")


class Equipment(object):

	def __init__(self, slot, power_bonus=0, defence_bonus=0, equipment_effect=None, max_health_bonus=0, light_radius_bonus=0, charges=0, activated=False, activation_func=None, deactivation_string="", wear_off_string="", chance_to_be_heard_modificator=0, chance_to_be_seen_modificator=0, chance_to_hear_modificator=0, chance_to_see_modificator=0, **kwargs):
		self.slot = slot
		self.power_bonus = power_bonus
		self.defence_bonus = defence_bonus
		self.equipment_effect = equipment_effect
		self.max_health_bonus = max_health_bonus
		self.light_radius_bonus = light_radius_bonus
		self.charges = charges
		self.max_charges = charges
		self.activated = activated
		self.activation_func = activation_func
		self.deactivation_string = deactivation_string # Must be a verb
		self.wear_off_string = wear_off_string # Must be a verb too
		self.chance_to_be_heard_modificator = chance_to_be_heard_modificator
		self.chance_to_be_seen_modificator = chance_to_be_seen_modificator
		self.chance_to_hear_modificator = chance_to_hear_modificator
		self.chance_to_see_modificator = chance_to_see_modificator
		self.kwargs = kwargs

	def activate(self, **kwargs):
		# this function only adds to the instance's attributes and manages activation func

		just_activated = False

		kwargs.update(self.kwargs)

		user = kwargs.get('user')
		eq_name = kwargs.get('eq_name')

		if self.activation_func is not None and not self.activated and self.charges > 0:
			if self.activation_func(**kwargs) == 'activated':
				self.activated = True
				just_activated = True

		if self.activation_func is not None and self.activated and not just_activated:
			self.activated = False
			user.send_message("{0} {1} {2}".format(user.name.title(), self.deactivation_string, eq_name.title()))

	def wear_off(self, user, eq_name):
		if self.activated and self.charges > 0: self.charges -= 1

		if self.charges <= 0: self.deactivate_from_wear(user, eq_name)


	def deactivate_from_wear(self, user, eq_name):
		self.activated = False
		user.send_message("{0}'s {1} {2}.".format(user.name.title(), eq_name.title(), self.wear_off_string))


class Effect(object): # timed effect
	def __init__(self, name, owner, activation_string, deactivation_string, duration, modificator=None, activation_func=None, deactivation_func=None):
		# effect must be a string
		self.name = name
		self.activation_string = activation_string
		self.deactivation_string = deactivation_string
		self.duration = duration
		self.modificator = modificator
		self.owner = owner

	def wear_off(self):
		if self.deactivation_func is not None:
			self.deactivation_func(**kwargs)
		self.owner.send_message("{0}!".format(deactivation_string))
		self.owner.effects.remove(self)

	def activate(self):
		if func is not None:
			self.func(**kwargs)
		self.owner.send_message("{0}!".format(activation_string))

	def update(self):
		self.duration -= 1

		if self.duration <= 0:
			self.wear_off()


class Container(object): # to have more loot in one place
	def __init__(self, loot=[]):
		self.loot = loot

	def open(self, ui, user):
		item_chosen = ui.draw_inventory_list(choose_item_text="Loot what?", title=self.owner.name.title(), container=self.loot, loot_all=True)
		if item_chosen is not None:
			if type(item_chosen) is not list:
				user.inventory.append(item_chosen)
				ui.add_item_to_UI(item_chosen)
				self.loot.remove(item_chosen)
			else:
				for item in item_chosen:
					user.inventory.append(item)
					ui.add_item_to_UI(item)
					self.loot.remove(item)
				# len(user.inventory)

	def put_inside(self, item):
		self.loot.append(item)


class SpellBook(object):
	pass

class Portal(object):
	pass

class Stairs(object):
	pass

def player_hurt_or_heal_knees(player, _map):

	max_knees = 10

	# player.fighter.is_overburdened()
	# player.fighter.knees

	if player.fighter.sneaking:
		player.fighter.knees -= 0.5 # add calculated value based on dexterity

	if not player.fighter.sneaking and player.fighter.knees < max_knees:
		# 'dd'
		player.fighter.knees += 0.1

	if (player.fighter.knees <= 0 and player.fighter.sneaking) or (player.fighter.knees <= 0 and player.fighter.is_overburdened):
		# 'dupsko'
		player_scream(player, _map)

def player_scream(player, _map):

	player.noise_made['range'] = 100
	player.noise_made['chance_to_be_heard'] = 1000
	player.noise_made['source'] = player
	player.noise_made['sound_name'] = "fuck"

	player.send_message("You scream: 'AH FUCK MY KNEES!'")



monsters = {'goblin': [constants.GOBLIN_MAX_HP,
					   constants.GOBLIN_ATTACK,
					   constants.GOBLIN_DEFENCE,
					   constants.GOBLIN_NAME,
					   constants.GOBLIN_SOUND_WALK,
					   constants.GOBLIN_MOD_TO_HEARING,
					   constants.GOBLIN_MOD_TO_SEEING,
					   constants.GOBLIN_AI,
				       constants.GOBLIN_SPAWN_RANGE,
				       constants.GOBLIN_SPAWN_CHANCE,
				       constants.GOBLIN_IMAGE_NAME,
				       constants.GOBLIN_MOD_TO_BE_SEEN,
				       constants.GOBLIN_MOD_TO_BE_HEARD
				       ],
			'worm':	  [constants.WORM_MAX_HP,
					   constants.WORM_ATTACK,
					   constants.WORM_DEFENCE,
					   constants.WORM_NAME,
					   constants.WORM_SOUND_WALK,
					   constants.WORM_MOD_TO_HEARING,
					   constants.WORM_MOD_TO_SEEING,
					   constants.WORM_AI,
				       constants.WORM_SPAWN_RANGE,
				       constants.WORM_SPAWN_CHANCE,
				       constants.WORM_IMAGE_NAME,
				       constants.WORM_MOD_TO_BE_SEEN,
				       constants.WORM_MOD_TO_BE_HEARD
					   ],
			'abhorrent_creature':	[constants.ABHORRENT_CREATURE_MAX_HP,
					   				 constants.ABHORRENT_CREATURE_ATTACK,
					   				 constants.ABHORRENT_CREATURE_DEFENCE,
					   				 constants.ABHORRENT_CREATURE_NAME,
					   				 constants.ABHORRENT_CREATURE_SOUND_WALK,
					   				 constants.ABHORRENT_CREATURE_MOD_TO_HEARING,
					   				 constants.ABHORRENT_CREATURE_MOD_TO_SEEING,
					   				 constants.ABHORRENT_CREATURE_AI,
				       				 constants.ABHORRENT_CREATURE_SPAWN_RANGE,
				       				 constants.ABHORRENT_CREATURE_SPAWN_CHANCE,
				       				 constants.ABHORRENT_CREATURE_IMAGE_NAME,
				       				 constants.ABHORRENT_CREATURE_MOD_TO_BE_SEEN,
				       				 constants.ABHORRENT_CREATURE_MOD_TO_BE_HEARD
					   ],
			}

materials = {}



# Dict of images and values of damage
weapons = {'type': {        
					'swords': []

					}
		  }


# PRIORITY IMG, (CHANCE, SPAWN RANGE), DEF, TO_BE_SEEN, TO_BE_HEARD, TO_SEE, TO_HEAR, WEIGHT, MAX_HEALTH_BONUS

chest_armor = {'material': {'bronze': [1, 'bronze_armor_IMG', (99, (1, 4)), 7, 0, 10, 0, 0, 10, 0],
							'copper': [2, 'copper_armor_IMG', (15, (1, 4)), 8, 0, 6, 0, 0, 6, 0],
							'steel':  [3, 'steel_armor_IMG', (10, (3, 5)), 12, 0, 12, 0, 0, 14, 0],
							'hardened steel': [4, 'hardened_steel_armor_IMG', (8, (3, 6)), 16, 0, 20, 0, 0, 20, 0],
							'crystal': [5, 'crystal_armor_IMG', (3, (5, 7)), 32, 20, 28, 0, 0, 30, 0]
						   }
						   
			  }

helmets = {}
boots = {}
cloaks = {}
accessories = {}
potions = {}
scrolls = {}



items = []

artifacts = {} # like crown of health, boots of silence, cloak of invisibility

# all generators have to return 'name': '' and 'data': IMG!!!

def gen_armor(level, _type, slot, equip_use_func, key):
	# equip_use_func to be passed in main, while generating the level

	armors_generated = []

	current_priority = 0

	materials = _type[key].keys()

	for x in materials:
		PRIORITY, IMG, CHANCE_SPAWN, DEF, TO_BE_SEEN, TO_BE_HEARD, TO_SEE, TO_HEAR, WEIGHT, MAX_HEALTH_BONUS = _type['material'][x]

		chance = CHANCE_SPAWN[0]
		_range = CHANCE_SPAWN[1]

		if current_priority < PRIORITY or current_priority == 0:
			if level in range(_range[0], _range[1]) or ((_range[0] ==_range[1]) and level == _range[0]):
				throw = random.randint(0, 100)
				if throw < chance:
					current_priority = PRIORITY
					eq_component = Equipment(slot, power_bonus=0, defence_bonus=DEF, equipment_effect=None, max_health_bonus=MAX_HEALTH_BONUS, light_radius_bonus=0, charges=0, activated=False, activation_func=None, deactivation_string="", wear_off_string="", chance_to_be_heard_modificator=TO_BE_HEARD, chance_to_be_seen_modificator=TO_BE_SEEN, chance_to_hear_modificator=TO_HEAR, chance_to_see_modificator=TO_SEE)
					item_component = Item(use_func=equip_use_func, equipment=eq_component, can_break=False, targetable=False, weight=WEIGHT, effect=None)
					armors_generated.append({"{0} {1}".format(str(x), slot) : item_component, 'data': IMG})

	return armors_generated

def gen_monsters(level, monsters, limit):

	monsters_to_place = []

	for x in range(limit):
		for mon in monsters:
			if level in range(monsters[mon][8][0], (monsters[mon][8][1])) or level == monsters[mon][8][0]:
				throw = random.randint(0, 100)

				if throw < monsters[mon][9]:
					monsters_to_place.append(monsters[mon])

	return monsters_to_place


if __name__ == '__main__':
	pass

	#gen_monsters(1, monsters, 20)
	

	#armors = []

	#for n in range(1):
	#	armor = gen_armor(3, chest_armor, 'breastplate', 'use_func', 'material')
	#	armors.extend(armor)

	#counter = 0
	#for n in armors:

	#	 n.keys()
		#if n.has_key('crystal breastplate'):
		#	counter += 1

	# counter