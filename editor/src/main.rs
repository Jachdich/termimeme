extern crate termion;

use termion::raw::IntoRawMode;
use termion::event::{Key, Event};
use std::io::{Write, stdout, stdin};
use crate::termion::input::TermRead;

#[derive(Copy, Clone, Debug)]
struct RGB {
	r: u8,
	g: u8,
	b: u8,
	default: bool,
}

impl RGB {
    fn new(r: u8, g: u8, b: u8) -> Self {
        RGB {
            r: r, g: g, b: b,
            default: false
        }
    }
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
    let mut bg = RGB::new(0, 0, 0);
    let mut fg = RGB::new(255, 255, 255);

    while pos < data.len() {
        if data[pos] == '\u{001b}' {
            pos += 2;
            if data[pos..pos + 2].to_vec().into_iter().collect::<String>() == "0m" {
                bg = RGB::new(0, 0, 0);
                fg = RGB::new(255, 255, 255);
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
                fg = RGB::new(r, g, b);
            } else if s == "48" {
                bg = RGB::new(r, g, b);
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

#[derive(PartialEq)]
enum Focus {
    Image,
    Toolbox,
    Charsheet,
}

#[derive(Debug, PartialEq)]
enum Tool {
    None,
    Pen,
    Paint,
    Text
}

fn main() {
	let stdout = stdout().into_raw_mode().unwrap();
	let mut screen = termion::input::MouseTerminal::from(stdout).into_raw_mode().unwrap();
	let contents =   std::fs::read_to_string("mem1.txt").unwrap();
	let char_sheet = std::fs::read_to_string("character_sheet.txt").unwrap();

	let mut data = make_data(contents.chars().collect::<Vec<char>>());
	let width: u16 = data[0].len() as u16;
	let height: u16 = data.len() as u16;
	
    let stdin = stdin();

    let mut img_cur_x: u16 = 3;
    let mut img_cur_y: u16 = 2;
    let mut curr_fg = RGB::new(0, 0, 0);
    let mut curr_bg = RGB::new(0, 0, 0);
//	println!("{:?}", data);
	write!(screen, "{}{}", termion::cursor::Hide, termion::clear::All).unwrap();

	let mut curr_buffer: String = construct_buffer(&data);

	//let mut image_shown = true;
	//let mut chars_shown = false;

    let mut pen_char: char = ' ';

	let mut focus = Focus::Image;
	let mut tool = Tool::None;
	let mut tool_down = false;

    for event in stdin.events() {
        let event = event.unwrap();
		match event.clone() {
			Event::Key(Key::Ctrl('c')) => break,
			Event::Key(Key::Ctrl('q')) => break,
			Event::Key(Key::Ctrl('s')) => {
				let mut file = std::fs::File::create("mem1.txt").unwrap();
				file.write_all(curr_buffer.replace("\r\n", "\n").as_bytes()).unwrap();
			},
			Event::Key(Key::Ctrl('e')) => {
			    
			},
			Event::Key(Key::Char('\t')) => {
			    if focus == Focus::Image {
			        focus = Focus::Toolbox;
			    } else if focus == Focus::Toolbox {
			        focus = Focus::Image;
			    }
			},
			_ => (),
		}		

        if focus == Focus::Image {
            match event.clone() {
                Event::Key(Key::Left) => img_cur_x -= 1,
    			Event::Key(Key::Right) => img_cur_x += 1,
    			Event::Key(Key::Up) => img_cur_y -= 1,
    			Event::Key(Key::Down) => img_cur_y += 1,
    			Event::Key(Key::Char('\n')) => tool_down = !tool_down,
    		    _ => (),
			}

			if !tool_down {
			    match event.clone() {
       			    Event::Key(Key::Char('t')) => {
           				tool = Tool::Text;
           			}
           			Event::Key(Key::Char('p')) => {
                        tool = Tool::Pen;
           			}
           			Event::Key(Key::Char('o')) => {
           			    tool = Tool::Paint;
           			}
           			_ => (),
       			}
			}
			if tool == Tool::Text && tool_down {
			    match event.clone() {
    			    Event::Key(Key::Char(c)) => {
        				data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].ch = c;
        				data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].fg = curr_fg;
        				img_cur_x += 1;
        				curr_buffer = construct_buffer(&data);
        			}
        			_ => (),
    			}
			} else if tool == Tool::Pen && tool_down {
			    if !curr_fg.default {
			        data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].fg = curr_fg;
			    }
			    if !curr_bg.default {
    		        data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].bg = curr_bg;
    		    }
    		    data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].ch = pen_char;
    		    curr_buffer = construct_buffer(&data);
			}
        }
		
		if img_cur_x < 1 { img_cur_x = 1; }
		if img_cur_y < 1 { img_cur_y = 1; }
		if img_cur_x > width  { img_cur_x = width; }
		if img_cur_y > height { img_cur_y = height; }

		write!(screen, "{}{}{}{}{}{}{}{}",
			termion::clear::All,
			termion::cursor::Goto(1, 1),
			curr_buffer,
			termion::cursor::Goto(img_cur_x, img_cur_y),
			termion::color::Bg(termion::color::Black),
			termion::color::Fg(termion::color::White),
			data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].ch,
			termion::cursor::Goto(img_cur_x, img_cur_y)
		).unwrap();

        write!(screen, "{}{:?}{}{}",
            termion::cursor::Goto(width + 1, 1),
            tool,
            termion::cursor::Goto(width + 1, 2),
            tool_down,
        ).unwrap();
		
		screen.flush().unwrap();
	}
}
