char bar() {
    return 'a';
}

int fib(int n) {
    if (n <= 1) {
        return n;
    } else {
        return fib(n-1) + fib(n-2);
    }
}

int unreach() {
    if (1) return 1;
    return 1 + fib(2);
}

int main() {
    print("Example program written in Sara");
    print(fib(10));
    print(bar());
    print("olá", 2, bar(), fib(10));
    print(fib(5), bar(), 2, "olá");
    return 0;
}
