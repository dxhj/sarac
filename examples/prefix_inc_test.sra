for_loop(int i): int {
    for (; i < 10; ++i)
        print(i, '\n');
    return i;
}

main(): int {
    int x;
    int a;
    int b;
    x = 1;
    a = ++x;
    b = x++;
    print(a, b, x);
    for_loop(0);
    return 0;
}
