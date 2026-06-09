import random

def start_game():
    print("\n-- Word Guessing Game --")
    words = []

    try:
        n = int(input("Enter how many words you want to add: "))
        for i in range(n):
            word = input(f"Enter word #{i+1}: ").strip()
            if word:
                words.append(word)
    except ValueError:
        print("❌ Invalid input. Please enter a number.")
        return 0

    if not words:
        print("⚠️ No words added. Game cancelled.")
        return 0

    secret_word = random.choice(words)
    print(f"\n🎯 A word has been chosen from your list of {len(words)} words. Start guessing!")

    guesses = 0
    for i in range(10):
        guesses += 1
        guess = input("Enter your guess: ").strip()

        if guess == secret_word:
            print(f"✅ Correct! You guessed the word '{secret_word}' in {guesses} tries!")
            return 10
        else:
            print("❌ Wrong word. Try again!")

    print(f"😢 You lost! The word was: '{secret_word}'")
    return 0
