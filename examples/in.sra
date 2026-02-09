bar(): char {
    return 'a';
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
    print("Example program written in Sara", 1+1, 1+1);
    print("oi", test_float, 1+1, 1+1, " ", 1.2, " ", 1.3 * 2, 10 / 2, 1.3 + 1);
    print(fib(10));
    print(bar());
    print("olá", 2, bar(), fib(10));
    print(fib(5), bar(), 2, "olá");
    return 0;
}
