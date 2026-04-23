import unittest

from pbir_builder import Grid, HStack, Padding, VStack


class LayoutContainerTests(unittest.TestCase):
    def test_hstack_resolves_equal_width_frames(self) -> None:
        frames = HStack(
            x=10,
            y=20,
            width=320,
            height=120,
            gap=10,
            padding=Padding.all(5),
        ).resolve(3)

        self.assertEqual(len(frames), 3)
        self.assertEqual(frames[0].x, 15)
        self.assertEqual(frames[0].y, 25)
        self.assertEqual(frames[0].width, 96.66666666666667)
        self.assertEqual(frames[0].height, 110)
        self.assertEqual(frames[1].x, 121.66666666666667)
        self.assertEqual(frames[2].x, 228.33333333333334)

    def test_vstack_resolves_equal_height_frames(self) -> None:
        frames = VStack(
            x=30,
            y=40,
            width=180,
            height=260,
            gap=12,
            padding=Padding.symmetric(horizontal=10, vertical=8),
        ).resolve(2)

        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0].x, 40)
        self.assertEqual(frames[0].y, 48)
        self.assertEqual(frames[0].width, 160)
        self.assertEqual(frames[0].height, 116)
        self.assertEqual(frames[1].y, 176)

    def test_grid_resolves_row_major_cells(self) -> None:
        frames = Grid(
            x=0,
            y=0,
            width=420,
            height=240,
            rows=2,
            columns=3,
            gap=10,
            padding=Padding.all(10),
        ).resolve(5)

        self.assertEqual(len(frames), 5)
        self.assertEqual(frames[0].x, 10)
        self.assertEqual(frames[0].y, 10)
        self.assertEqual(frames[0].width, 126.66666666666667)
        self.assertEqual(frames[0].height, 105)
        self.assertEqual(frames[1].x, 146.66666666666669)
        self.assertEqual(frames[3].x, 10)
        self.assertEqual(frames[3].y, 125)

    def test_grid_rejects_over_capacity_layout(self) -> None:
        grid = Grid(x=0, y=0, width=100, height=100, rows=1, columns=2)

        with self.assertRaisesRegex(ValueError, "Grid capacity exceeded"):
            grid.resolve(3)


if __name__ == "__main__":
    unittest.main()
