int main(int y, int parameters) {
    int x;
    char c = 'a';
    x = 1;
    x = 3;
    return 0;
}

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

int foo() {
    return 1 + foo();
}