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
    fn from_html(n: u32) -> Self {
    	let r: u8 = ((n >> 16) & 0xFF) as u8;
    	let g: u8 = ((n >> 8)  & 0xFF) as u8;
    	let b: u8 = ((n >> 0)  & 0xFF) as u8;
    	RGB {
    		r:r, g:g, b:b, default:false
    	}
    }
    fn to_fg(&self) -> termion::color::Fg<termion::color::Rgb> {
    	return termion::color::Fg(termion::color::Rgb(self.r, self.g, self.b));
    }
    fn to_bg(&self) -> termion::color::Bg<termion::color::Rgb> {
    	return termion::color::Bg(termion::color::Rgb(self.r, self.g, self.b));
    }
    fn get_inverted(&self) -> RGB {
    	let txt_col: RGB;
        if self.r as u16 + self.g as u16 + self.b as u16 > 384 {
        	txt_col = RGB::new(0, 0, 0);
        } else {
        	txt_col = RGB::new(255, 255, 255);
        }
        return txt_col;
    }

    fn to_html_string(&self) -> String {
    	if self.default {
    		return "default".to_string();
    	}
    	format!("#{:02X?}{:02X?}{:02X?}", self.r, self.g, self.b)
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

fn draw_colour_select<W: Write>(
		screen: &mut termion::input::MouseTerminal<W>,
		x: u16, y: u16,
		tool_cur_x: u16, tool_cur_y: u16,
		colours: &Vec<RGB>, 
		curr_fg: RGB, curr_bg: RGB) {
    for row in 0..4 as usize {
       	write!(screen, "{}{}{}█{}█{}█{}█", 
			termion::cursor::Goto(x, row as u16 + y),
			termion::color::Bg(termion::color::Reset),
			colours[row * 4 + 0].to_fg(),
			colours[row * 4 + 1].to_fg(),
			colours[row * 4 + 2].to_fg(),
			colours[row * 4 + 3].to_fg(),
       	).unwrap();
    }

	let sel = colours[((tool_cur_y - 1) * 4 + (tool_cur_x - 1)) as usize];
	write!(screen, "{}{}{}╳", 
		termion::cursor::Goto((tool_cur_x - 1) + x, (tool_cur_y - 1) + y),
		sel.get_inverted().to_fg(),
		sel.to_bg(),
	).unwrap();

	write!(screen, "{}{}{}{}{}{}{}{}",
		termion::cursor::Goto(x, y + 4),
		curr_fg.to_bg(),
		curr_fg.get_inverted().to_fg(),
		curr_fg.to_html_string(),
		termion::cursor::Goto(x, y + 5),
		curr_bg.to_bg(),
		curr_bg.get_inverted().to_fg(),
		curr_bg.to_html_string(),
	).unwrap();
}

fn make_char_sheet(txt: String) -> Vec<Vec<char>> {
	let mut ret: Vec<Vec<char>> = Vec::new();
	let arr_1d: Vec<char> = txt.chars().collect::<Vec<char>>();
	ret.push(Vec::new());
	for ch in arr_1d {
		if ch == '\n' {
			ret.push(Vec::new());
		} else {
			ret.last_mut().unwrap().push(ch);
		}
	}
	while ret.len() > 0 && ret.last().unwrap().len() == 0 {
		ret.pop();
	}
	ret
}

fn main() {
	let stdout = stdout().into_raw_mode().unwrap();
	let screen = termion::screen::AlternateScreen::from(stdout).into_raw_mode().unwrap();
	let mut screen = termion::input::MouseTerminal::from(screen).into_raw_mode().unwrap();
	let contents =       std::fs::read_to_string("mem1.txt").unwrap();
	let char_sheet_txt = std::fs::read_to_string("character_sheet.txt").unwrap();
	let char_sheet = make_char_sheet(char_sheet_txt);
	
	let colours = [0xffffff, 0xffff01, 0xff6600, 0xde0000,
			       0xff0198, 0x330099, 0x0001cd, 0x0098fe,
				   0x01ab02, 0x016701, 0x673301, 0x9a6634,
				   0xbbbbbb, 0x888888, 0x444444, 0x000000].iter().map(|x| RGB::from_html(*x)).collect::<Vec<RGB>>();

	let mut data = make_data(contents.chars().collect::<Vec<char>>());
	let width: u16 = data[0].len() as u16;
	let height: u16 = data.len() as u16;
	
    let stdin = stdin();

    let mut img_cur_x: u16 = 3;
    let mut img_cur_y: u16 = 2;

	let mut tool_cur_x: u16 = 1;
	let mut tool_cur_y: u16 = 1;

	let mut char_cur_x: u16 = 3;
	let mut char_cur_y: u16 = 6;
    
    let mut curr_fg = RGB::new(0, 0, 0);
    let mut curr_bg = RGB::new(255, 255, 255);
//	println!("{:?}", data);
	write!(screen, "{}{}", termion::cursor::Hide, termion::clear::All).unwrap();

	let mut curr_buffer: String = construct_buffer(&data);

	//let mut image_shown = true;
	//let mut chars_shown = false;

    let mut pen_char: char = '█';

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
		    	if focus != Focus::Charsheet {
		    		focus = Focus::Charsheet;
		    	} else {
		    		focus = Focus::Image; //TODO ??
		    	}
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

		if focus == Focus::Toolbox {
			match event.clone() {
				Event::Key(Key::Left) => tool_cur_x -= 1,
    			Event::Key(Key::Right) => tool_cur_x += 1,
    			Event::Key(Key::Up) => tool_cur_y -= 1,
    			Event::Key(Key::Down) => tool_cur_y += 1,
    			Event::Key(Key::Char('\n')) => {
    				curr_fg = colours[((tool_cur_y - 1) * 4 + (tool_cur_x - 1)) as usize];
    			},
    			Event::Key(Key::Backspace) => {
    				curr_bg = colours[((tool_cur_y - 1) * 4 + (tool_cur_x - 1)) as usize];
    			},
    			Event::Key(Key::Char('d')) => {
    				curr_fg.default = !curr_fg.default;
    			},
				Event::Key(Key::Ctrl('d')) => {
    				curr_bg.default = !curr_bg.default;
    			},
    			_ => ()
			}
			if tool_cur_x < 1 { tool_cur_x = 1; }
			if tool_cur_y < 1 { tool_cur_y = 1; }
			if tool_cur_x > 4  { tool_cur_x = 4; }
			if tool_cur_y > 4 { tool_cur_y = 4; }
			
		}

		if focus == Focus::Charsheet {
			match event.clone() {
				Event::Key(Key::Left) => char_cur_x -= 1,
    			Event::Key(Key::Right) => char_cur_x += 1,
    			Event::Key(Key::Up) => char_cur_y -= 1,
    			Event::Key(Key::Down) => char_cur_y += 1,
    			_ => (),
			}
			if char_cur_x < 1 { char_cur_x = 1; }
			if char_cur_y < 1 { char_cur_y = 1; }
			if char_cur_x > char_sheet[0].len() as u16 { char_cur_x = char_sheet[0].len() as u16; }
			if char_cur_y > char_sheet.len() as u16 { char_cur_y = char_sheet.len() as u16; }
			pen_char = char_sheet[char_cur_y as usize - 1][char_cur_x as usize - 1];
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
			if img_cur_x < 1 { img_cur_x = 1; }
			if img_cur_y < 1 { img_cur_y = 1; }
			if img_cur_x > width  { img_cur_x = width; }
			if img_cur_y > height { img_cur_y = height; }

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
			    	Event::Key(Key::Char('\n')) => (),
    			    Event::Key(Key::Char(c)) => {
        				data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].ch = c;
						if !curr_fg.default {
					        data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].fg = curr_fg;
					    }
					    if !curr_bg.default {
		    		        data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].bg = curr_bg;
		    		    }
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
			} else if tool == Tool::Paint && tool_down {
				if !curr_fg.default {
			        data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].fg = curr_fg;
			    }
			    if !curr_bg.default {
    		        data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].bg = curr_bg;
    		    }
    		    curr_buffer = construct_buffer(&data);
			}
        }
		let cur_fg: termion::color::Fg<termion::color::Rgb>;
		let cur_bg: termion::color::Bg<termion::color::Rgb>;
		if (tool == Tool::Paint || tool == Tool::Pen) && tool_down {
			cur_bg = curr_bg.to_bg();
			cur_fg = curr_fg.to_fg();
		} else {
			cur_bg = termion::color::Bg(termion::color::Rgb(0, 0, 0));
			cur_fg = termion::color::Fg(termion::color::Rgb(255, 255, 255));
			
		}


		write!(screen, "{}{}{}{}{}{}{}{}{}",
			termion::color::Bg(termion::color::Reset),
			termion::clear::All,
			termion::cursor::Goto(1, 1),
			curr_buffer,
			termion::cursor::Goto(img_cur_x, img_cur_y),
			cur_fg,
			cur_bg,
			data[(img_cur_y - 1) as usize][(img_cur_x - 1) as usize].ch,
			termion::cursor::Goto(img_cur_x, img_cur_y)
		).unwrap();

        write!(screen, "{}{}{:?}{}{}",
        	termion::color::Bg(termion::color::Reset),
            termion::cursor::Goto(width + 1, 1),
            tool,
            termion::cursor::Goto(width + 1, 2),
            tool_down,
        ).unwrap();

        draw_colour_select(&mut screen, width + 1, 3, tool_cur_x, tool_cur_y, &colours, curr_fg, curr_bg);

		let mut x: u16 = 0;
		let mut y: u16 = 0;
		for line in &char_sheet {
			for ch in line {
				write!(screen, "{}{}{}{}",
					termion::cursor::Goto(width + 9 + x, y + 2),
					termion::color::Fg(termion::color::Reset),
					termion::color::Bg(termion::color::Reset),
					ch).unwrap();
				x += 2;
			}
			y += 2;
			x = 0;
		}

		write!(screen, "{}╭─╮{}│{}│{}╰─╯",
			termion::cursor::Goto(width + 9 + (char_cur_x - 1) * 2 - 1, 2 + (char_cur_y - 1) * 2 - 1),
			termion::cursor::Goto(width + 9 + (char_cur_x - 1) * 2 - 1, 2 + (char_cur_y - 1) * 2),
			termion::cursor::Goto(width + 9 + (char_cur_x - 1) * 2 + 1, 2 + (char_cur_y - 1) * 2),
			termion::cursor::Goto(width + 9 + (char_cur_x - 1) * 2 - 1, 2 + (char_cur_y - 1) * 2 + 1),
		).unwrap();
		
		screen.flush().unwrap();
	}
	write!(screen, "{}", termion::cursor::Show).unwrap();
}
