// Kotlin Quick Playground
// Write your Kotlin code here. If you omit 'fun main()',
// the runner will automatically wrap it in a main function!

println("Hello from Kotlin!")

val list = listOf("Apple", "Banana", "Cherry")
for ((index, fruit) in list.withIndex()) {
    println("${index + 1}: $fruit")
}
