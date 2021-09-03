import re, random, os, pygame, sys
# CONSTANTS
# Width of play arena
WIDTH = 1185
# Height of play arena
HEIGHT = 720
# Size of cell in pixels
CELLSIZE = 35
# Grid dimension (n*m)
GRID_DIM = (32, 16)
# Start position for drawing cells in grid (in pixels)
GRID_START_COORD = (32, 127)
# Position and size for various buttons and panels in pixels
RESTART_BUTTON_COORD = (558, 35)
RESTART_BUTTON_SIZE = (64, 59)
HIGHSCORE_BUTTON_COORD = (777, 46)
HIGHSCORE_BUTTON_SIZE = (106, 38)
HIGHSCORE_PANEL_COORD = (301, 120)
HIGHSCORE_PANEL_SIZE = (583, 430)
CHANGE_NAME_COORD = (688, 502)
CHANGE_NAME_SIZE = (106, 38)
# Position of text labels in pixels
MINES_LEFT_LABEL_POS = (50, 40)
TIME_LABEL_POS = (1040, 40)
# Time between clicks for double click
DOUBLE_CLICK_TIME = 200
# Amount of mines spawned
MINE_COUNT = 100
# Radius of no mines from first click
EMPTY_RADIUS = 3
# Misc
PLAYER_NAME = "DEV"


def resource_path(relative_path):
    try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# CELL OBJECT
class Cell(pygame.Rect):
    def __init__(self, left, top, width, height, textures, idx, grid):
        pygame.Rect.__init__(self, left, top, width, height)
        self.hidden_tex = textures[0]
        self.revealed_tex = textures[1]
        self.mine_tex = textures[2]
        self.mine_red_tex = textures[3]
        self.mine_green_tex = textures[4]
        self.flag_tex = textures[5]
        self.number_tex = None
        self.idx = idx
        self.grid = grid
        self.is_revealed = False
        self.is_mine = False
        self.flagged = False
        self.number = -1
        self.held = False
        self.highlight = 0

        self.exploded_mine = (-1, -1)

    def place_mine(self):
        self.is_mine = True

    def set_num(self, number, number_tex):
        self.number = number
        if number > 0:
            self.number_tex = number_tex

    def clicked(self, leftclick, double_click):
        if leftclick:  # left click
            if self.is_revealed and self.number > 0 and double_click:
                succesful_flag_count, self.exploded_mine = self.grid.get_cell_minecount(self.idx[0], self.idx[1],
                                                                                        flags_override=True)
                if succesful_flag_count == self.number:
                    if self.exploded_mine:
                        return -3  # Exit code 3 means player double clicked a cell with wrong flags around it (and is now dead)
                    self.search_and_reveal()
            else:
                return self.reveal(True)
        else:  # right click
            if self.is_revealed:
                return 0  # Exit code 0 means nothing special happened
            self.flagged = not self.flagged
            if self.flagged and self.is_mine:
                return 1  # Exit code 1 means a mine was flagged
            elif not self.flagged and self.is_mine:
                return -1  # Exit code -1 means a mine was unflagged
            elif self.flagged and not self.is_mine:
                return 4  # Exit code 3 means an empty cell was flagged
            elif not self.flagged and not self.is_mine:
                return -4  # Exit code 4 means an empty cell was unflagged
            else:
                return 0

    def reveal(self, player_click, reveal_all=False):
        """ 'A technically recursive function is still a recursive function' -Author """
        if self.flagged and not reveal_all:
            return 0
        if self.is_mine and player_click:
            self.is_revealed = True
            return -2  # Exit code -2 means player clicked mine (and is now dead)
        elif self.is_mine:
            return 0  # See exit code 0 in clicked()
        elif self.number > 0:
            self.is_revealed = True
            return 0  # See above
        self.is_revealed = True
        if player_click:
            self.search_and_reveal()
        else:
            return 2  # Exitcode 2 means search_and_reveal() should append the cell to it's search queue
        return 0  # See above

    def search_and_reveal(self):
        queue = [self.idx]
        seen = [self.idx]
        while len(queue) > 0:
            for i in range(queue[0][0] - 1, queue[0][0] + 2):
                for j in range(queue[0][1] - 1, queue[0][1] + 2):
                    if not (i < 0 or i > GRID_DIM[1] - 1 or j < 0 or j > GRID_DIM[0] - 1) \
                            and (i, j) not in seen and not self.grid.cells[i][j].is_revealed:
                        seen.append((i, j))
                        exit_code = self.grid.cells[i][j].reveal(False)
                        if exit_code == 2:
                            queue.append((i, j))
            queue = queue[1:]

    def draw(self, screen):
        if self.is_revealed:
            screen.blit(self.revealed_tex, self.topleft)
            if self.is_mine:
                if self.highlight == 1:
                    screen.blit(self.mine_red_tex, self.topleft)
                elif self.highlight == 2:
                    screen.blit(self.mine_green_tex, self.topleft)
                else:
                    screen.blit(self.mine_tex, self.topleft)
            elif self.number > 0:
                screen.blit(self.number_tex, self.topleft)
        else:
            if self.flagged:
                screen.blit(self.hidden_tex, self.topleft)
                screen.blit(self.flag_tex, self.topleft)
            elif self.held:
                screen.blit(self.revealed_tex, self.topleft)
            else:
                screen.blit(self.hidden_tex, self.topleft)


# GRID OBJECT
class Grid(object):
    def __init__(self, cell_textures, number_tex_list):
        self.cells = []
        self.cell_textures = cell_textures
        self.number_tex_list = number_tex_list
        self.create_grid()

    def create_grid(self):
        self.cells = []
        pos = GRID_START_COORD
        for i in range(GRID_DIM[1]):
            row = []
            for j in range(GRID_DIM[0]):
                new_cell = Cell(pos[0], pos[1], CELLSIZE, CELLSIZE, self.cell_textures, (i, j), self)
                row.append(new_cell)
                pos = (pos[0] + CELLSIZE, pos[1])
            self.cells.append(row)
            pos = (GRID_START_COORD[0], pos[1] + CELLSIZE)

    def place_mines(self, mine_amount, first_click_idx, empty_radius):
        """ Place mines is called after first click so the player never clicks a mine on first click.
            There is also some radius of empty cells from the players first click """
        remaining_positions = []
        for i in range(GRID_DIM[1]):
            for j in range(GRID_DIM[0]):
                dist_from_click = max(first_click_idx[0], i) - min(first_click_idx[0], i) \
                                  + max(first_click_idx[1], j) - min(first_click_idx[1], j)
                if dist_from_click > empty_radius:
                    remaining_positions.append((i, j))
        if mine_amount >= len(remaining_positions):
            mine_amount = remaining_positions
        while mine_amount > 0:
            rand_idx = random.randint(0, len(remaining_positions) - 1)
            rand_pos = remaining_positions[rand_idx]
            del remaining_positions[rand_idx]
            self.cells[rand_pos[0]][rand_pos[1]].place_mine()
            mine_amount -= 1

        self.distribute_numbers()

    def distribute_numbers(self):
        for i in range(GRID_DIM[1]):
            for j in range(GRID_DIM[0]):
                if self.cells[i][j].is_mine:
                    continue
                num, cell = self.get_cell_minecount(i, j)
                self.cells[i][j].set_num(num, self.number_tex_list[num - 1])

    def get_cell_minecount(self, row, col, flags_override=False):
        count = 0
        mine_exploded = None
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if i < 0 or i > GRID_DIM[1] - 1 or j < 0 or j > GRID_DIM[0] - 1:
                    continue
                cell = self.cells[i][j]
                if flags_override:
                    if cell.flagged:
                        count += 1
                    elif cell.is_mine and not cell.flagged:
                        mine_exploded = cell
                else:
                    if cell.is_mine:
                        count += 1
        return count, mine_exploded

    def reveal_all_mines(self):
        for i in range(GRID_DIM[1]):
            for j in range(GRID_DIM[0]):
                if self.cells[i][j].is_mine:
                    self.cells[i][j].reveal(True, True)

    def reveal_all(self):
        for i in range(GRID_DIM[1]):
            for j in range(GRID_DIM[0]):
                self.cells[i][j].reveal(True, True)
                if self.cells[i][j].is_mine:
                    self.cells[i][j].highlight = 2  # Set to green highlight

    def get_clicked_cell(self, click_pos):
        for i in range(GRID_DIM[1]):
            for j in range(GRID_DIM[0]):
                if self.cells[i][j].collidepoint(click_pos):
                    return self.cells[i][j]
        return None

    def draw(self, screen):
        for i in range(GRID_DIM[1]):
            for j in range(GRID_DIM[0]):
                self.cells[i][j].draw(screen)


# GAME MANAGER
class GameManager(object):
    def __init__(self):
        pygame.init()
        logo = pygame.image.load(resource_path("img/interface/minesweeper_logo.png"))
        pygame.display.set_icon(logo)
        pygame.display.set_caption("Minesweeper")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.background_tex = pygame.image.load(resource_path("img/interface/background.png"))
        self.cell_textures = [
            pygame.image.load(resource_path("img/cell/cell_hidden.png")),
            pygame.image.load(resource_path("img/cell/cell_revealed.png")),
            pygame.image.load(resource_path("img/cell/mine.png")),
            pygame.image.load(resource_path("img/cell/mine_red.png")),
            pygame.image.load(resource_path("img/cell/mine_green.png")),
            pygame.image.load(resource_path("img/cell/flag.png"))
        ]
        self.number_tex_list = [
            pygame.image.load(resource_path("img/numbers/num_1.png")),
            pygame.image.load(resource_path("img/numbers/num_2.png")),
            pygame.image.load(resource_path("img/numbers/num_3.png")),
            pygame.image.load(resource_path("img/numbers/num_4.png")),
            pygame.image.load(resource_path("img/numbers/num_5.png")),
            pygame.image.load(resource_path("img/numbers/num_6.png")),
            pygame.image.load(resource_path("img/numbers/num_7.png")),
            pygame.image.load(resource_path("img/numbers/num_8.png"))
        ]
        self.restart_button_list = [
            pygame.image.load(resource_path("img/restart_button/restart_button_green.png")),
            pygame.image.load(resource_path("img/restart_button/restart_button_yellow.png")),
            pygame.image.load(resource_path("img/restart_button/restart_button_red.png")),
            pygame.image.load(resource_path("img/restart_button/restart_button_green_clicked.png")),
            pygame.image.load(resource_path("img/restart_button/restart_button_yellow_clicked.png")),
            pygame.image.load(resource_path("img/restart_button/restart_button_red_clicked.png"))
        ]
        self.restart_button_rect = pygame.Rect(RESTART_BUTTON_COORD, RESTART_BUTTON_SIZE)
        # Highscore button
        self.highscore_button_tex = pygame.image.load(resource_path("img/interface/highscore.png"))
        self.highscore_button_clicked_tex = pygame.image.load(resource_path("img/interface/highscore_clicked.png"))
        self.highscore_cur_tex = self.highscore_button_tex
        self.highscore_button_rect = pygame.Rect(HIGHSCORE_BUTTON_COORD, HIGHSCORE_BUTTON_SIZE)
        # Highscore panel
        self.highscore_panel_tex = pygame.image.load(resource_path("img/interface/highscore_menu.png"))
        self.highscore_panel_rect = pygame.Rect(HIGHSCORE_PANEL_COORD, HIGHSCORE_PANEL_SIZE)
        self.showing_highscores = False
        self.highscore_list = []
        # Change name button
        self.change_name_button_tex = pygame.image.load(resource_path("img/interface/change_name_button.png"))
        self.change_name_button_clicked_tex = pygame.image.load(resource_path("img/interface/change_name_button_clicked.png"))
        self.change_name_button_changing_tex = pygame.image.load(resource_path("img/interface/change_name_button_changing.png"))
        self.change_name_cur_tex = self.change_name_button_tex
        self.change_name_button_rect = pygame.Rect(CHANGE_NAME_COORD, CHANGE_NAME_SIZE)
        self.changing_name = False
        self.ui_font = pygame.font.SysFont("monospace", 50, True)
        self.highscore_font = pygame.font.SysFont("monospace", 30, True)
        self.name_font = pygame.font.SysFont("monospace", 25, True)

        self.player_name = PLAYER_NAME

        ##################
        # This part should match restart_game()
        self.grid = Grid(self.cell_textures, self.number_tex_list)
        self.is_alive = True
        self.mines_placed = False
        self.mines_flagged = 0
        self.empty_flagged = 0
        self.restart_button_state = 0
        self.time_elapsed = 0
        self.last_frame_time = pygame.time.get_ticks()
        ##################

        # For input
        self.left_mouse_held = False
        self.last_left_click = 0
        self.right_mouse_held = False
        self.last_cell_held = None

    def play_game(self):
        running = True
        while running:
            if self.is_alive and self.mines_placed and not self.showing_highscores:
                self.update_time()

            self.last_frame_time = pygame.time.get_ticks()

            if len(self.player_name) == 3:
                self.changing_name = False

            if self.changing_name:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return -1
                    if event.type == pygame.KEYDOWN:
                        if (ord('a') <= event.key <= ord('z')) or event.key in [ord('æ'), ord('ø'), ord('å')]:
                            self.player_name += chr(event.key).upper()
            else:
                input_exit_code = self.handle_input()
                if input_exit_code == -1:
                    running = False
                elif input_exit_code == 1:
                    self.restart_game()

            self.draw_game()

    def update_time(self):
        now = pygame.time.get_ticks()
        self.time_elapsed += now - self.last_frame_time

    def restart_game(self):
        self.grid = Grid(self.cell_textures, self.number_tex_list)
        self.is_alive = True
        self.mines_placed = False
        self.mines_flagged = 0
        self.empty_flagged = 0
        self.restart_button_state = 0
        self.time_elapsed = 0
        self.last_frame_time = pygame.time.get_ticks()

    def handle_input(self):
        mouse_button_state = pygame.mouse.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_released = False
        if mouse_button_state[0] and not self.left_mouse_held:
            self.left_mouse_held = True
        elif not mouse_button_state[0] and self.left_mouse_held:
            self.left_mouse_held = False
            mouse_released = True

        # Restart button
        if self.restart_button_state > 2:
            self.restart_button_state -= 3
        if self.left_mouse_held and self.restart_button_rect.collidepoint(mouse_pos) and self.restart_button_state < 3:
            self.restart_button_state += 3
        if mouse_released and self.restart_button_rect.collidepoint(mouse_pos):
            return 1

        # Highscore button
        self.highscore_cur_tex = self.highscore_button_tex
        mouse_over_highscore = self.highscore_button_rect.collidepoint(mouse_pos)
        if self.left_mouse_held and mouse_over_highscore:
            self.highscore_cur_tex = self.highscore_button_clicked_tex
        if mouse_released and mouse_over_highscore:
            self.toggle_highscore_panel()

        if self.showing_highscores:
            # Change button
            self.change_name_cur_tex = self.change_name_button_tex
            mouse_over_change_name = self.change_name_button_rect.collidepoint(mouse_pos)
            if self.left_mouse_held and mouse_over_change_name:
                self.change_name_cur_tex = self.change_name_button_clicked_tex
            if mouse_released and mouse_over_change_name:
                self.change_name()

        if self.last_cell_held:
            self.last_cell_held.held = False
        clicked_cell = self.grid.get_clicked_cell(mouse_pos)
        if self.restart_button_state == 1:
            self.restart_button_state = 0
        if self.left_mouse_held and clicked_cell and not clicked_cell.is_revealed:
            clicked_cell.held = True
            self.last_cell_held = clicked_cell
            if self.is_alive and not clicked_cell.flagged:
                self.restart_button_state = 1
        elif mouse_released or mouse_button_state[2]:
            if clicked_cell and self.is_alive and not self.showing_highscores:
                double_click = False
                if mouse_released:
                    now = pygame.time.get_ticks()
                    if now - self.last_left_click < DOUBLE_CLICK_TIME:
                        double_click = True
                    self.last_left_click = now
                if not self.mines_placed:
                    self.grid.place_mines(MINE_COUNT, clicked_cell.idx, EMPTY_RADIUS)
                    self.mines_placed = True
                if (mouse_released and not clicked_cell.flagged) or (
                        mouse_button_state[2] and not self.right_mouse_held):
                    self.right_mouse_held = True
                    clicked_exit_code = clicked_cell.clicked(mouse_released, double_click)
                    if clicked_exit_code == 1:
                        self.mines_flagged += 1
                    elif clicked_exit_code == -1:
                        self.mines_flagged -= 1
                    elif clicked_exit_code == 4:
                        self.empty_flagged += 1
                    elif clicked_exit_code == -4:
                        self.empty_flagged -= 1
                    elif clicked_exit_code == -2:
                        self.player_dies(clicked_cell)
                    elif clicked_exit_code == -3:
                        self.player_dies(clicked_cell.exploded_mine)

        elif not mouse_button_state[2] and self.right_mouse_held:
            self.right_mouse_held = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return -1

        if self.mines_flagged == MINE_COUNT and self.empty_flagged == 0 and self.is_alive:
            self.player_wins()

    def player_dies(self, clicked_mine_cell):
        self.is_alive = False
        self.grid.reveal_all_mines()
        self.restart_button_state = 2
        clicked_mine_cell.highlight = True

    def player_wins(self):
        self.is_alive = False
        self.grid.reveal_all()
        self.try_save_highscore(int(self.time_elapsed / 1000), self.player_name)

    def draw_game(self):
        self.screen.blit(self.background_tex, (0, 0))
        self.grid.draw(self.screen)
        self.draw_ui()
        pygame.display.flip()

    def draw_ui(self):
        self.screen.blit(self.restart_button_list[self.restart_button_state], self.restart_button_rect.topleft)
        self.screen.blit(self.highscore_cur_tex, self.highscore_button_rect.topleft)
        if self.showing_highscores:
            self.draw_highscore_panel()
        # Remaining mines label
        mines_left_count = MINE_COUNT - (self.mines_flagged + self.empty_flagged)
        if mines_left_count < -99:
            mines_left_count = -99
        mines_left_label = self.ui_font.render("%03d" % mines_left_count, 1, (250, 34, 28))
        self.screen.blit(mines_left_label, MINES_LEFT_LABEL_POS)
        # Time label
        time_in_seconds = min(int(self.time_elapsed / 1000), 999)
        time_label = self.ui_font.render("%03d" % time_in_seconds, 1, (250, 34, 28))
        self.screen.blit(time_label, TIME_LABEL_POS)

    def draw_highscore_panel(self):
        self.screen.blit(self.highscore_panel_tex, self.highscore_panel_rect.topleft)
        self.load_highscores()
        text_pos = (self.highscore_panel_rect.topleft[0] + 100, self.highscore_panel_rect.topleft[1] + 20)
        ypos = text_pos[1]
        for i in range(len(self.highscore_list)):
            highscores_label = self.highscore_font.render(self.highscore_list[i], 1, (0, 26, 65))
            self.screen.blit(highscores_label, (text_pos[0], ypos))
            ypos += 35
        name_label = self.name_font.render("My name is %s" % self.player_name, 1, (0, 26, 65))
        self.screen.blit(name_label, (text_pos[0] + 40, ypos + 18))
        if not self.changing_name:
            self.screen.blit(self.change_name_cur_tex, self.change_name_button_rect.topleft)
        else:
            self.screen.blit(self.change_name_button_changing_tex, self.change_name_button_rect.topleft)

    def toggle_highscore_panel(self):
        self.showing_highscores = not self.showing_highscores

    def try_save_highscore(self, new_score, name):
        highscores = []
        new_highscore = False
        with open(resource_path("highscores.txt"), "r") as hf:
            for line in hf:
                highscore_object = self.parse_highscore_line(line)
                highscores.append(highscore_object)
        for i in range(len(highscores)):
            if highscores[i][1] > new_score:
                highscores = highscores[:i + 1] + highscores[i:9]
                highscores[i] = (name.upper(), new_score)
                new_highscore = True
                break
        if len(highscores) < 10 and not new_highscore:
            new_highscore = True
            highscores.append((name.upper(), new_score))
        with open(resource_path("highscores.txt"), "w") as hf:
            for highscore in highscores:
                hf.write("%s %d\n" % (highscore[0], highscore[1]))

        return new_highscore

    def load_highscores(self):
        res = []
        count = 0
        with open(resource_path("highscores.txt"), "r") as hf:
            for line in hf:
                count += 1
                highscore_object = self.parse_highscore_line(line)
                res.append("%02d:......%s......%03d" % (count, highscore_object[0], highscore_object[1]))
        self.highscore_list = res

    def parse_highscore_line(self, line):
        highscore_match = re.search("([a-zA-Z]*) ([0-9]*)", line)
        if highscore_match:
            return (highscore_match.group(1), int(highscore_match.group(2)))
        return None

    def change_name(self):
        self.player_name = ""
        self.changing_name = True


def main():
    gamemanager = GameManager()
    gamemanager.play_game()


if __name__ == "__main__":
    main()

