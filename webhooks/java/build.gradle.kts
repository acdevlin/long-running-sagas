plugins {
    java
}

repositories {
    mavenCentral()
}

dependencies {
    // Conductor's agent SDK, which also provides the workflow, task and worker clients.
    implementation("org.conductoross:conductor-client-ai:6.0.1")
    implementation("io.github.cdimascio:dotenv-java:3.2.0")
    implementation("org.xerial:sqlite-jdbc:3.53.4.0")
    // The SDK logs through SLF4J 1.7; src/main/resources/simplelogger.properties sets the level.
    runtimeOnly("org.slf4j:slf4j-simple:1.7.36")
}

tasks.withType<JavaCompile>().configureEach {
    // Java 21 is the oldest version the Conductor SDK supports; any newer JDK can build for it.
    options.release = 21
    // Keeps method parameter names, which the SDK reads to describe each agent tool's inputs.
    options.compilerArgs.add("-parameters")
}

// One task per codelab step, so that `./gradlew deploy-workflow` compiles and runs that step.
listOf("create-db", "deploy-workflow", "serve-agent", "send-webhook", "query-db").forEach { step ->
    tasks.register<JavaExec>(step) {
        group = "codelab"
        description = "Runs the $step step of the webhooks codelab."
        classpath = sourceSets.main.get().runtimeClasspath
        mainClass = "io.orkes.codelab.webhooks.Main"
        args(step)
        // sqlite-jdbc loads a native library, which newer JDKs warn about unless it is allowed.
        jvmArgs("--enable-native-access=ALL-UNNAMED")
    }
}
