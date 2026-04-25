declare i32 @printf(i8* noundef, ...)

@.str.print0 = private unnamed_addr constant [6 x i8] c"%d%c\0A\00"
define i32 @for_loop(i32 %i) {
  %1 = alloca i32
  store i32 %i, i32* %1
  br label %bb0
bb0:
  %2 = load i32, i32* %1
  %3 = add i32 0, 10
  %4 = icmp slt i32 %2, %3
  br i1 %4, label %bb1, label %bb3
bb1:
  %5 = load i32, i32* %1
  %6 = add i8 0, 10
  %7 = getelementptr inbounds [6 x i8], [6 x i8]* @.str.print0, i32 0, i32 0
  %8 = zext i8 %6 to i32
  %9 = call i32 (i8*, ...) @printf(i8* noundef %7, i32 noundef %5, i32 noundef %8)
  br label %bb2
bb2:
  %10 = load i32, i32* %1
  %11 = add i32 0, 1
  %12 = add i32 %10, %11
  store i32 %12, i32* %1
  br label %bb0
bb3:
  %13 = load i32, i32* %1
  ret i32 %13
}

@.str.print1 = private unnamed_addr constant [8 x i8] c"%d%d%d\0A\00"
define i32 @main() {
  %1 = alloca i32
  %2 = alloca i32
  %3 = alloca i32
  %4 = add i32 0, 1
  store i32 %4, i32* %1
  %5 = load i32, i32* %1
  %6 = add i32 0, 1
  %7 = add i32 %5, %6
  store i32 %7, i32* %1
  store i32 %7, i32* %2
  %8 = load i32, i32* %1
  %9 = add i32 0, 1
  %10 = add i32 %8, %9
  store i32 %10, i32* %1
  store i32 %8, i32* %3
  %11 = load i32, i32* %2
  %12 = load i32, i32* %3
  %13 = load i32, i32* %1
  %14 = getelementptr inbounds [8 x i8], [8 x i8]* @.str.print1, i32 0, i32 0
  %15 = call i32 (i8*, ...) @printf(i8* noundef %14, i32 noundef %11, i32 noundef %12, i32 noundef %13)
  %16 = call i32 @for_loop()
  %17 = add i32 0, 0
  ret i32 %17
}
