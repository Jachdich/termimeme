#include <ncurses.h>
#include <ctype.h>
#include <string>
#include <signal.h>
#include <vector>
#include <fstream>
#include <iostream>
#include <sstream>

struct ScreenPos {
    int x;
    int y;
    ScreenPos() {}
    ScreenPos(int x, int y) {
        this->x = x;
        this->y = y;
    }
    ScreenPos operator-(const ScreenPos &other) {
        int x = this->x - other.x;
        int y = this->y - other.y;
        if (x < 0) x = 0;
        if (y < 0) y = 0;
        return ScreenPos(x, y);
    }

    ScreenPos operator+=(const ScreenPos& other) {
        this->x += other.x;
        this->y += other.y;
        return ScreenPos(this->x, this->y);
    }

    ScreenPos operator+(const ScreenPos& other) {
        return ScreenPos(this->x + other.x, this->y + other.y);
    }

    void setBounds(ScreenPos max) {
        if (x < 0) x = 0;
        if (y < 0) y = 0;
        if (x > max.x) x = max.x;
        if (y > max.y) y = max.y;
    }
};

std::vector<ScreenPos> posStack;

ScreenPos getPos() {
    int x,y;
    getyx(stdscr, y, x);
    return ScreenPos(x, y);
}

void setPos(ScreenPos pos) {
    wmove(stdscr, pos.y, pos.x);
}

void pushPos() {
    posStack.push_back(getPos());
}

void popPos() {
    ScreenPos pos = posStack.back();
    posStack.pop_back();
    setPos(pos);
}

ScreenPos max;
ScreenPos pos;
bool guiRunning = true;

int main() {
    initscr();
    raw();
    cbreak();
    noecho();
    keypad(stdscr, TRUE);
    int y,x;
    getmaxyx(stdscr, y, x);
    max = ScreenPos(x - 1, y - 1);
    pos = ScreenPos(0, 0);
    setPos(pos);
    while (guiRunning) {
        mainLoop();
    }
    endwin();
    return 0;
}