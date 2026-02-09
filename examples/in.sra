char bar() {
    return 'a';
}

int fib(int n) {
    if (n >= 1) {
        return n;
    } else {
        return fib(n-1) + fib(n-2);
    }
}

int unreach() {
    if (1) return 1;
    return 1 + fib(2);
}

int main(int y, int parameters) {
    int x;
    string str;
    char c = 'a';
    x = 1 + str;
    x = 3;
    print(fib(10));
    return 0;
}
