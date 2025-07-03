
while True:
    try:
        n = int(input())
        break
    except ValueError:
        print()


i = 0


while i < n:
    valor_a = input()
    valor_b = input()

    if valor_a[-len(valor_b):] == valor_b:
        print("encaixa")
    else:
        print("nao encaixa")

    i += 1
