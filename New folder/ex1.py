print("--- FILE MENU ---")
print("1. Write to File")
print("2. Read File")
print("3. Append to File")
print("4. Copy File")
print("5. Exit")

while True:
    choice = int(input("\nEnter your choice: "))

    # Write
    if choice == 1:
        f = open("sample.txt", "w")
        data = input("Enter data to write: ")
        f.write(data)
        f.close()
        print("Data written successfully")

    # Read
    elif choice == 2:
        f = open("sample.txt", "r")
        print("\nFile Content:")
        print(f.read())
        f.close()

    # Append
    elif choice == 3:
        f = open("sample.txt", "a")
        data = input("Enter data to append: ")
        f.write("\n" + data)
        f.close()
        print("Data appended successfully")

    # Copy
    elif choice == 4:
        f1 = open("sample.txt", "r")
        f2 = open("copy.txt", "w")
        f2.write(f1.read())
        f1.close()
        f2.close()
        print("File copied successfully")

    # Exit
    elif choice == 5:
        print("Program ended")
        break

    else:
        print("Invalid choice")