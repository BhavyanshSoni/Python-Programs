import random

class Player:
    def __init__(self, player_number):
        self.name = input(f"Enter name for Player {player_number}: ")
        self.position = 0

    def roll_dice(self):
        return random.randint(1, 6)

# Snakes and Ladders board
snakes = {
    17: 10,   # Moderate decrease
    54: 34,   # Moderate decrease
    62: 45,   # Moderate decrease
    64: 60,   # Small decrease
    87: 60,   # Moderate decrease
    93: 73,   # Moderate decrease
    95: 85,   # Small decrease
    98: 89,   # Moderate decrease
}

ladders = {
    3: 5,     # Climb to 5
    5: 11,    # Climb to 11
    11: 18,   # Climb to 18
    20: 29,   # Climb to 29
    27: 38,   # Climb to 38
    21: 35,   # Climb to 35
    17: 23,   # Moderate climb (instead of 93)
    19: 28,   # Moderate climb (instead of 63)
}

# Get number of players
num_players = int(input("How many players will play 🎮 ? "))
players = [Player(i + 1) for i in range(num_players)]

print("\n🎲 Game Start! First to reach exactly 100 wins! 🎯\n")

winner = None
while not winner:
    for player in players:
        input(f"{player.name}, press Enter to roll the dice... ")
        roll = player.roll_dice()
        print(f"{player.name} rolled a {roll} 🎲!")

        player.position += roll
        print(f"{player.name} is now at position {player.position}.\n")

        # Check if player hit a snake
        if player.position in snakes:
            player.position = snakes[player.position]
            print(f"Oops! {player.name} hit a snake and is now at position {player.position}.")

        # Check if player climbed a ladder
        if player.position in ladders:
            player.position = ladders[player.position]
            print(f"Wow! {player.name} climbed a ladder and is now at position {player.position}.")

        # Check if player has won
        if player.position == 100:
            winner = player
            break
        elif player.position > 100:
            print(f"Oops! {player.name}'s score went over 100! Going back to 0.")
            player.position = 0

print(f"\n🎉 {winner.name} wins the game with exactly 100! 🏆")
