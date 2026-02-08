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

int foo() {
    return 1 + bar();
}