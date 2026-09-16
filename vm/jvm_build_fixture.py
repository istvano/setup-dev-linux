"""Synthetic build acceptance; invoked only after guest identity/storage guards."""
from pathlib import Path
import os
import subprocess
import xml.etree.ElementTree as ET


def check(fixture):
    root = fixture / 'jvm-builds'
    root.mkdir()
    maven = root / 'maven'
    main = maven / 'src/main/java'
    tests = maven / 'src/test/java'
    main.mkdir(parents=True)
    tests.mkdir(parents=True)
    source = 'public class Fixture { public static int answer() { return 6 * 7; } public static void main(String[] args) { if (answer() != 42) throw new AssertionError(); System.out.println(answer()); } }\n'
    (main / 'Fixture.java').write_text(source)
    test_source = tests / 'FixtureTest.java'
    passing_test = 'import org.junit.jupiter.api.Test; import static org.junit.jupiter.api.Assertions.*; class FixtureTest { @Test void answer() { assertEquals(42, Fixture.answer()); } }\n'
    test_source.write_text(passing_test)
    (maven / 'pom.xml').write_text('''<project xmlns="http://maven.apache.org/POM/4.0.0">
<modelVersion>4.0.0</modelVersion><groupId>invalid.example</groupId><artifactId>fixture</artifactId><version>1</version>
<properties><maven.compiler.release>25</maven.compiler.release><project.build.sourceEncoding>UTF-8</project.build.sourceEncoding></properties>
<dependencies><dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId><version>6.1.3</version><scope>test</scope></dependency></dependencies>
<build><plugins>
<plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId><version>3.16.0</version></plugin>
<plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-surefire-plugin</artifactId><version>3.6.0</version></plugin>
</plugins></build></project>
''')
    (root / 'settings.xml').write_text('<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"/>\n')
    gradle = root / 'gradle'
    (gradle / 'src/main/java').mkdir(parents=True)
    (gradle / 'src/main/java/Fixture.java').write_text(source)
    (gradle / 'settings.gradle').write_text("rootProject.name = 'gradle-fixture'\n")
    (gradle / 'build.gradle').write_text("plugins { id 'java' }\ntasks.register('smoke', JavaExec) { dependsOn classes; classpath = sourceSets.main.runtimeClasspath; mainClass = 'Fixture' }\ncheck.dependsOn smoke\n")
    (root / 'Hello.kt').write_text('fun main() { check(6 * 7 == 42); println("kotlin-ok") }\n')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('MAVEN_', 'GRADLE_', 'JAVA_', 'JDK_JAVA_', '_JAVA_')) and k not in ('BASH_ENV', 'ENV', 'CLASSPATH')}
    def shell(body, expected=0):
        result = subprocess.run(['zsh', '-i', '-c', 'set -e\n' + body, '--', str(root)],
                                env=env, text=True, capture_output=True, timeout=300)
        if (result.returncode == 0) != (expected == 0):
            print(result.stdout[-6000:])
            print(result.stderr[-3000:])
            raise AssertionError('JVM build fixture unexpected exit')
        return result
    maven_command = 'mvn -B -C -s "$1/settings.xml" -gs "$1/settings.xml" -Dmaven.repo.local="$1/maven-cache"'
    shell('cd "$1/maven"\n' + maven_command + ' package\n[[ "$(java -cp target/fixture-1.jar Fixture)" == 42 ]]')
    report = maven / 'target/surefire-reports/TEST-FixtureTest.xml'
    results = ET.parse(report).getroot()
    assert results.get('tests') == '1' and results.get('failures') == '0' and results.get('errors') == '0'
    test_source.write_text(passing_test.replace('assertEquals(42,', 'assertEquals(41,'))
    shell('cd "$1/maven"\n' + maven_command + ' -o test', expected=1)
    assert ET.parse(report).getroot().get('failures') == '1'
    test_source.write_text(passing_test)
    shell('cd "$1/maven"\n' + maven_command + ' -o package')
    shell('cd "$1/gradle"\ngradle --offline --no-daemon -g "$1/gradle-cache" build\n[[ "$(java -cp build/libs/gradle-fixture.jar Fixture)" == 42 ]]')
    shell('kotlinc "$1/Hello.kt" -include-runtime -d "$1/hello.jar"\n[[ "$(java -jar "$1/hello.jar")" == kotlin-ok ]]')
    shell('''maven_path=$(command -v mvn)
gradle_path=$(command -v gradle)
kotlin_path=$(command -v kotlinc)
sdk use java 21.0.12.1.1-ws-ms
[[ "$(command -v mvn)" == "$maven_path" ]]
[[ "$(command -v gradle)" == "$gradle_path" ]]
[[ "$(command -v kotlinc)" == "$kotlin_path" ]]
sdk use java 25.0.4.1.1-ws-tem
sdk current java | grep -F 'Current default java version 25.0.4.1.1-ws-tem'
''')
    print('PASS: Maven test/package and failing-test recovery, offline Gradle build/run, Kotlin JAR/run and stable tool paths across Java switching')


def check_native(fixture):
    root = fixture / 'native-build'
    root.mkdir()
    (root / 'NativeFixture.java').write_text('public class NativeFixture { public static void main(String[] args) { if (6 * 7 != 42) throw new AssertionError(); System.out.println("native-ok"); } }\n')
    body = '''set -e
cd "$1"
sdk use java 25.0.4.1-ws-mandrel
export GRAALVM_HOME="$JAVA_HOME"
native-image --version
javac NativeFixture.java
native-image --no-fallback -O1 -J-Xmx3g NativeFixture native-fixture
[[ "$(./native-fixture)" == native-ok ]]
sdk use java 25.0.4.1.1-ws-tem
sdk current java | grep -F 'Current default java version 25.0.4.1.1-ws-tem'
'''
    env = {k: v for k, v in os.environ.items() if not k.startswith(('JAVA_', 'JDK_JAVA_', '_JAVA_', 'GRAALVM_', 'NATIVE_IMAGE_')) and k not in ('BASH_ENV', 'ENV', 'CLASSPATH')}
    result = subprocess.run(['zsh', '-i', '-c', body, '--', str(root)], env=env, capture_output=True, text=True, timeout=600)
    if result.returncode:
        print(result.stdout[-7000:])
        print(result.stderr[-3000:])
        raise AssertionError('Mandrel native build failed')
    assert (root / 'native-fixture').read_bytes().startswith(b'\x7fELF')
    print('PASS: Mandrel compiles Java to a native ELF executable with no fallback, runs it and retains Temurin 25 default')
