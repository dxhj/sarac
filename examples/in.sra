bar(): char {
    return 'a';
}

loop(): void {
    int n = 0;
    print("here");
    while (n < 10) {
        n = n + 1;
        print(n);
    }

    for (; n > 0; n--) {
        print(n);
    }
}

shift_test(char type, int n): int {
    if (type == 'l') {
        return n << 2;
    } else if (type == 'r') {
        return n >> 2;
    }
}

fib(int n): int {
    if (n <= 1) {
        return n;
    } else {
        return fib(n-1) + fib(n-2);
    }
}

unreach(): int {
    if (1) return 1;
    return 1 + fib(2);
}

main(): int {
    float test_float = 10;
    print("Example program written in Sara\n\n");
    print(shift_test('l', 10));
    print(shift_test('r', 10));
    print("oi", test_float, 1+1, 1+1, " ", 1.2, " ", 1.3 * 2, 10 / 2, 1.3 + 1);
    print(fib(10));
    print(bar());
    print("olá", 2, bar(), fib(10));
    print(fib(5), bar(), 2, "olá");
    loop();
    return 0;
}
