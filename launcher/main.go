// Лаунчер Windows: двойной клик по exe → запуск приложения (как run.bat).
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"unsafe"
)

func main() {
	base, err := exeDir()
	if err != nil {
		fatal("Не удалось определить папку программы:\n" + err.Error())
	}
	if err := os.Chdir(base); err != nil {
		fatal("Не удалось открыть папку программы:\n" + err.Error())
	}

	appMarker := filepath.Join(base, "app", "__main__.py")
	if _, err := os.Stat(appMarker); err != nil {
		fatal("Рядом с exe не найдена папка app.\nПоложите VoiceToText.exe в корень проекта.")
	}

	py, err := findPython()
	if err != nil {
		fatal("Python не найден.\n\nУстановите Python 3.11+ с python.org\nи отметьте «Add python.exe to PATH».\n\n" + err.Error())
	}

	venvPython := filepath.Join(base, ".venv", "Scripts", "python.exe")
	venvPythonw := filepath.Join(base, ".venv", "Scripts", "pythonw.exe")

	if _, err := os.Stat(venvPython); err != nil {
		info("Первый запуск: создаю окружение и ставлю зависимости.\nЭто займёт несколько минут.")
		if err := run(py, "-m", "venv", ".venv"); err != nil {
			fatal("Не удалось создать виртуальное окружение:\n" + err.Error())
		}
		if err := run(venvPython, "-m", "pip", "install", "--upgrade", "pip"); err != nil {
			fatal("Не удалось обновить pip:\n" + err.Error())
		}
		req := filepath.Join(base, "requirements.txt")
		if err := run(venvPython, "-m", "pip", "install", "-r", req); err != nil {
			fatal("Не удалось установить зависимости:\n" + err.Error())
		}
	}

	runner := venvPythonw
	if _, err := os.Stat(runner); err != nil {
		runner = venvPython
	}

	cmd := exec.Command(runner, "-m", "app")
	cmd.Dir = base
	hideConsole(cmd)
	if err := cmd.Start(); err != nil {
		fatal("Не удалось запустить приложение:\n" + err.Error())
	}
}

func exeDir() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	exe, err = filepath.EvalSymlinks(exe)
	if err != nil {
		return "", err
	}
	return filepath.Dir(exe), nil
}

func findPython() (string, error) {
	candidates := []string{"py", "python", "python3"}
	var tried []string
	for _, name := range candidates {
		path, err := exec.LookPath(name)
		if err != nil {
			tried = append(tried, name)
			continue
		}
		// py -3 предпочтительнее на Windows
		if name == "py" {
			cmd := exec.Command(path, "-3", "--version")
			hideConsole(cmd)
			if out, err := cmd.CombinedOutput(); err == nil && strings.Contains(strings.ToLower(string(out)), "python") {
				return path + "|-3", nil // маркер для run()
			}
			tried = append(tried, "py -3")
			continue
		}
		cmd := exec.Command(path, "--version")
		hideConsole(cmd)
		if out, err := cmd.CombinedOutput(); err == nil && strings.Contains(strings.ToLower(string(out)), "python") {
			return path, nil
		}
		tried = append(tried, name)
	}
	return "", fmt.Errorf("проверено: %s", strings.Join(tried, ", "))
}

func run(pythonSpec string, args ...string) error {
	var cmd *exec.Cmd
	if strings.Contains(pythonSpec, "|") {
		parts := strings.SplitN(pythonSpec, "|", 2)
		all := append([]string{parts[1]}, args...)
		cmd = exec.Command(parts[0], all...)
	} else {
		cmd = exec.Command(pythonSpec, args...)
	}
	hideConsole(cmd)
	out, err := cmd.CombinedOutput()
	if err != nil {
		msg := strings.TrimSpace(string(out))
		if msg != "" {
			return fmt.Errorf("%v\n%s", err, msg)
		}
		return err
	}
	return nil
}

func hideConsole(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
}

func info(msg string) {
	messageBox("Voice to Text", msg, 0x40) // MB_ICONINFORMATION
}

func fatal(msg string) {
	messageBox("Voice to Text", msg, 0x10) // MB_ICONERROR
	os.Exit(1)
}

func messageBox(title, text string, flags uint32) {
	user32 := syscall.NewLazyDLL("user32.dll")
	proc := user32.NewProc("MessageBoxW")
	proc.Call(
		0,
		uintptr(unsafe.Pointer(syscall.StringToUTF16Ptr(text))),
		uintptr(unsafe.Pointer(syscall.StringToUTF16Ptr(title))),
		uintptr(flags),
	)
}
