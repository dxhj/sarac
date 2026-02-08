define i32 @main(i32 %y, i32 %parameters) {
  %1 = alloca i32
  %2 = alloca i32
  %3 = alloca i32
  %4 = alloca i32
  store i32 %y, i32* %3
  store i32 %parameters, i32* %4
  %5 = add i32 0, 97
  store i32 %5, i32* %1
  %6 = add i32 0, 49
  store i32 %6, i32* %2
  %7 = add i32 0, 51
  store i32 %7, i32* %2
  %8 = add i32 0, 48
  ret i32 %8
}

define i8 @bar() {
  %1 = add i32 0, 97
  %2 = trunc i32 %1 to i8
  ret i8 %2
}

define i32 @fib(i32 %n) {
  %1 = alloca i32
  store i32 %n, i32* %1
  %2 = load i32, i32* %1
  %3 = add i32 0, 49
  %4 = icmp sge i32 %2, %3
  br i1 %4, label %bb0, label %bb1
bb0:
  %5 = load i32, i32* %1
  ret i32 %5
bb1:
  %6 = load i32, i32* %1
  %7 = add i32 0, 49
  %8 = sub i32 %6, %7
  %9 = call i32 @fib(i32 %8)
  %10 = load i32, i32* %1
  %11 = add i32 0, 50
  %12 = sub i32 %10, %11
  %13 = call i32 @fib(i32 %12)
  %14 = add i32 %9, %13
  ret i32 %14
}

define i32 @unreach() {
  %1 = add i32 0, 49
  %2 = icmp ne i32 %1, 0
  br i1 %2, label %bb0, label %bb0
bb0:
  %3 = add i32 0, 49
  ret i32 %3
}
