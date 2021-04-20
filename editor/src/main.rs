extern crate termion;

use termion::raw::IntoRawMode;
use termion::event::{Key, Event};
use std::io::{Write, stdout, stdin};
use crate::termion::input::TermRead;

#[derive(Copy, Clone, Debug)]
struct RGB {
	r: u8,
	g: u8,
	b: u8
}

#[derive(Copy, Clone, Debug)]
struct FmtChar {
	ch: char,
	fg: RGB,
	bg: RGB,
}

fn read_until(ch: char, data: &Vec<char>, mut pos: usize) -> (Vec<char>, usize) {
    let start = pos;
    while data[pos] != ch {
    	pos += 1;
    }
    (data[start..pos].to_vec(), pos)
}
/*    
fn is_24bit(data: &Vec<char>) -> bool {
    let mut pos = 0;
    while data[pos] != '\u{001b}' &&
    	   pos < data.len() - 7 &&
    	   data[pos + 1] != '[' {
    	pos += 1;
    }
    if pos == data.len() - 8 { return false; }
    let (_first_num, pos)  = read_until(';', data, pos + 2);
    let (second_num, _pos) = read_until(';', data, pos + 1);
    if second_num[0] == '2' { return true; }
    if second_num[0] == '5' { return false; }
    return false;
}*/

fn make_data(data: Vec<char>) -> Vec<Vec<FmtChar>> {
    let mut out: Vec<FmtChar> = Vec::new();
    let mut pos = 0;
    let mut bg = RGB{r: 0, g: 0, b: 0};
    let mut fg = RGB{r: 255, g: 255, b: 255};

    while pos < data.len() {
        if data[pos] == '\u{001b}' {
            pos += 2;
            if data[pos..pos + 2].to_vec().into_iter().collect::<String>() == "0m" {
                bg = RGB{r: 0, g: 0, b: 0};
                fg = RGB{r: 255, g: 255, b: 255};
                pos += 2;
                continue;
            }
            let (first_num,   npos) = read_until(';', &data, pos); pos = npos;
            let (_second_num, npos) = read_until(';', &data, pos + 1); pos = npos;

            let (rv, npos) = read_until(';', &data, pos + 1); pos = npos;
            let (gv, npos) = read_until(';', &data, pos + 1); pos = npos;
            let (bv, npos) = read_until('m', &data, pos + 1); pos = npos;
            let r = rv.into_iter().collect::<String>().parse::<u8>().unwrap();
            let g = gv.into_iter().collect::<String>().parse::<u8>().unwrap();
            let b = bv.into_iter().collect::<String>().parse::<u8>().unwrap();
            pos += 1;
            let s: String = first_num.into_iter().collect();
            if s == "38" {
                fg = RGB{r, g, b};
            } else if s == "48" {
                bg = RGB{r, g, b};
            }
        } else {
            out.push(FmtChar{ch: data[pos], fg: fg, bg: bg});
            pos += 1;
        }
    }
    let mut n: Vec<Vec<FmtChar>> = Vec::new();
    n.push(Vec::new());
    for ch in out {
    	if ch.ch == '\n' {
    		n.push(Vec::new());
    	} else {
    		n.last_mut().unwrap().push(ch);
    	}
    }
    if n.last().unwrap().len() == 0 {
    	n.pop();
    }
    return n;
}

fn construct_buffer(data: &Vec<Vec<FmtChar>>) -> String {
	let mut buffer = "".to_string();
	for e in data {
		for ch in e {
			buffer.push_str(&termion::color::Fg(termion::color::Rgb(ch.fg.r, ch.fg.g, ch.fg.b)).to_string());
			buffer.push_str(&termion::color::Bg(termion::color::Rgb(ch.bg.r, ch.bg.g, ch.bg.b)).to_string());
			buffer.push(ch.ch);
		}
		buffer.push_str("\r\n");
	}
	buffer
}

fn main() {
	let stdout = stdout().into_raw_mode().unwrap();
	let mut screen = termion::input::MouseTerminal::from(stdout).into_raw_mode().unwrap();
	let contents =   std::fs::read_to_string("mem0.txt").unwrap();
	let char_sheet = std::fs::read_to_string("character_sheet.txt").unwrap();

	let mut data = make_data(contents.chars().collect::<Vec<char>>());
	let width: u16 = data[0].len() as u16;
	let height: u16 = data.len() as u16;
	
    let stdin = stdin();

    let mut x: u16 = 3;
    let mut y: u16 = 2;
    let mut curr_fg = RGB{r: 0, g: 0, b: 0};
    let mut curr_bg = RGB{r: 255, g: 255, b: 255};
//	println!("{:?}", data);
	write!(screen, "{}{}", termion::cursor::Hide, termion::clear::All).unwrap();

	let mut curr_buffer: String = construct_buffer(&data);

    for event in stdin.events() {

		match event.unwrap() {
			Event::Key(Key::Ctrl('c')) => break,
			Event::Key(Key::Ctrl('q')) => break,
			Event::Key(Key::Ctrl('s')) => {
				let mut file = std::fs::File::create("mem0.txt").unwrap();
				file.write_all(curr_buffer.as_bytes()).unwrap();
			},
			Event::Key(Key::Left) => x -= 1,
			Event::Key(Key::Right) => x += 1,
			Event::Key(Key::Up) => y -= 1,
			Event::Key(Key::Down) => y += 1,
			Event::Key(Key::Char('\n')) => y += 1,
			Event::Key(Key::Char(c)) => {
				data[(y - 1) as usize][(x - 1) as usize].ch = c;
				data[(y - 1) as usize][(x - 1) as usize].fg = curr_fg;
				x += 1;
				curr_buffer = construct_buffer(&data);
			}
			_ => (),
		}
		if x < 1 { x = 1; }
		if y < 1 { y = 1; }
		if x > width  { x = width; }
		if y > height { y = height; }

		write!(screen, "{}{}{}{}{}{}{}{}",
			termion::clear::All,
			termion::cursor::Goto(1, 1),
			curr_buffer,
			termion::cursor::Goto(x, y),
			termion::color::Bg(termion::color::Black),
			termion::color::Fg(termion::color::White),
			data[(y - 1) as usize][(x - 1) as usize].ch,
			termion::cursor::Goto(x, y)
		).unwrap();
		screen.flush().unwrap();
	}
}
