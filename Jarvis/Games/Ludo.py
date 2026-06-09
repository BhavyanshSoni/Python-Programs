import random
import re  # For regular expression to validate player names

class LudoGame:
    def __init__(self, num_players):
        self.num_players = num_players
        self.players = []
        self.token_positions = {}
        self.finished = {player: False for player in range(num_players)}
        self.token_colors = ['🔴', '🟢', '🔵', '🟡']  # Red, Green, Blue, Yellow
        self.player_names = []

        # Ask for player names and colors
        for i in range(num_players):
            name = self.get_valid_name(i + 1)  # Get a valid name
            color = self.token_colors[i]
            self.players.append((name, color))
            self.token_positions[name] = [0, 0, 0, 0]  # 4 tokens for each player
            self.player_names.append(name)

        self.turn = 0  # Start with the first player

    def get_valid_name(self, player_num):
        while True:
            name = input(f"Enter name for Player {player_num}: ").strip()  # Remove extra spaces
            if re.match("^[A-Za-z ]+$", name):  # Name should only have alphabets and spaces
                return name
            else:
                print("❌ Invalid name! Name should only contain letters and spaces. Please try again.")

    def roll_dice(self):
        return random.randint(1, 6)

    def move_token(self, player, token_index, roll):
        if self.token_positions[player][token_index] == 0:  # Token is in the home area
            if roll == 6:  # Player needs a 6 to move out of the home area
                print(f"🎉 {player} gets a token out of the home!")
                self.token_positions[player][token_index] = 1
            else:
                print(f"❌ {player} rolled {roll}, but needs a 6 to move out of the home area.")
        else:
            self.token_positions[player][token_index] += roll
            if self.token_positions[player][token_index] > 30:
                self.token_positions[player][token_index] = 30  # Ensure it doesn't go past 30 (finish line)
            print(f"🏃‍♂️ {player} moved Token {token_index + 1} to position {self.token_positions[player][token_index]}.")

    def check_winner(self):
        for player in self.players:
            name, color = player
            if all(position == 30 for position in self.token_positions[name]):
                return name
        return None

    def print_board(self):
        print("\n--- Current Positions ---")
        for player, color in self.players:
            positions = ', '.join([str(pos) for pos in self.token_positions[player]])  # Fix here
            print(f"{color} {player}: {positions}")
        print("--------------------------")

    def play_turn(self):
        current_player = self.players[self.turn][0]
        print(f"\n🎲 {current_player}'s Turn!")
        roll = self.roll_dice()
        print(f"  🎲 Rolled: {roll}")

        # Let the player choose which token to move
        print("  Choose a token to move (1-4):")
        print("  1: Token 1 | 2: Token 2 | 3: Token 3 | 4: Token 4")
        
        # Adding exception handling for invalid token selection
        while True:
            try:
                token_choice = int(input(f"  {current_player}, select a token to move: "))
                if token_choice < 1 or token_choice > 4:
                    raise ValueError("Token choice must be between 1 and 4.")
                break  # Break the loop if the selection is valid
            except ValueError as ve:
                print(f"❌ Invalid input: {ve}. Please select a valid token (1-4).")
            except Exception as e:
                print(f"❌ Unexpected error: {e}. Please try again.")

        # Move the selected token (convert 1-based index to 0-based index for internal processing)
        self.move_token(current_player, token_choice - 1, roll)
        self.print_board()

        # Check if there's a winner
        winner = self.check_winner()
        if winner:
            print(f"\n🎉 {winner} wins the game! 🏆")
            return True  # Game over
        return False  # Continue the game

    def play_game(self):
        while True:
            try:
                if self.play_turn():
                    break  # Game over
                self.turn = (self.turn + 1) % self.num_players  # Switch to the next player
            except Exception as e:
                print(f"❌ An error occurred during the game: {e}")
                break  # In case of unexpected errors during the game

# Main game setup with exception handling
while True:
    try:
        num_players = int(input("How many players will play (2-4)? "))
        if num_players < 2 or num_players > 4:
            raise ValueError("The number of players must be between 2 and 4.")
        break  # Exit the loop if input is valid
    except ValueError as ve:
        print(f"❌ Invalid input: {ve}. Please enter a number between 2 and 4.")

game = LudoGame(num_players)
game.play_game()
