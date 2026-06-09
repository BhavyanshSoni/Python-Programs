import random

def start_game():
    print("\n-- Rock Paper Scissors --")
    choices = ["R", "P", "S"]
    score = 0

    for i in range(10):
        user_input = input("Enter your choice (R/P/S): ").upper()
        if user_input not in choices:
            print("❌ Invalid input. Choose R, P or S.")
            continue

        comp_choice = random.choice(choices)
        print(f"You chose: {user_input} | Computer chose: {comp_choice}")

        if comp_choice == user_input:
            print("🤝 It's a Tie!")
            score += 1
        elif (user_input == "R" and comp_choice == "S") or \
             (user_input == "P" and comp_choice == "R") or \
             (user_input == "S" and comp_choice == "P"):
            print("✅ You Won!")
            score += 2
        else:
            print("❌ You Lost!")

    print(f"\n🎯 Your RPS Score: {score}/20")
    return score
