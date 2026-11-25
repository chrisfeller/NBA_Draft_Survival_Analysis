import pandas as pd
from functools import reduce
import difflib
from lifelines import KaplanMeierFitter
import matplotlib.pyplot as plt

plt.style.use('fivethirtyeight')

def fuzzy_name_match(x, prospect_names):
    """
    Fuzzy matches a given player's names from an individual mock draft with
    the player's 'true' name in full prospect list.

    Args:
        x (str): an individual player's name
        prospect_names (list): player names from the full prospect list

    Returns:
        x (str): fuzzy match of input player's name from full prospect list,
                 or None if there is no match
    """
    matches = difflib.get_close_matches(x, prospect_names)
    return matches[0] if matches else None

def pre_process_mocks(df, prospect_names):
    """
    Updates each player name in a given mock draft with the fuzzy match name
    from the full prospect list. Allows all mock drafts to be easily joined
    together as not all mock's follow the same naming conventions. For example,
    some mocks have Xavier Tillman Sr. and others have Xavier Tillman.

    Prints every name that was not an exact match so it can be checked, drops
    names with no match, and raises an error if two names in the same mock
    match the same prospect.

    Args:
        df (pandas DataFrame): an individual mock draft
        prospect_names (list): player names from the full prospect list

    Returns:
        df (pandas DataFrame): an individual mock draft with player names
                               updated to fuzzy match name from full prospect
                               list
    """
    mock_name = [col for col in df.columns if col != 'player'][0].replace('_rank', '')
    # create fuzzy match name for each player, which will be used as join
    # column when merging with other mock drafts
    df['fuzzy_name'] = df['player'].apply(lambda x: fuzzy_name_match(x, prospect_names))
    # report non-exact matches so a wrong match (e.g. a prospect missing from
    # prospects.csv being matched to a similarly named player) can be caught
    for player, fuzzy_name in df.loc[df['player'] != df['fuzzy_name'],
                                     ['player', 'fuzzy_name']].values:
        if fuzzy_name is None:
            print('{0}: no match for "{1}", dropped'.format(mock_name, player))
        else:
            print('{0}: matched "{1}" to "{2}"'.format(mock_name, player, fuzzy_name))
    # two names matching the same prospect would duplicate that player's rows
    # when the mock drafts are merged
    dupes = df.loc[df['fuzzy_name'].notnull() & df['fuzzy_name'].duplicated(keep=False)]
    if not dupes.empty:
        raise ValueError('{0}: multiple names matched the same prospect:\n{1}'
                         .format(mock_name, dupes[['player', 'fuzzy_name']].to_string()))
    # drop unmatched names, as merging on null names would pair every
    # unmatched name in one mock draft with every unmatched name in the next
    df = df.dropna(subset=['fuzzy_name'])
    # drop original player name
    df = df.drop('player', axis=1)
    return df

def plot_player(player, melt_df, save=False):
    """
    Plots the survival curve for an individual player either displaying the
    output or saving to the `../plots/players` directory.

    Args:
        player (str): The name of an individual player from the full
                      prospect list
        melt_df (pandas DataFrame): long-form big board dataframe with duration
                                    and censor columns
        save (boolean): Boolean of whether to write out the .png file in the
                        `../plots/players` director or display the image

    Returns:
        None
    """
    # instantiate Kaplan-Meier survival model
    kmf = KaplanMeierFitter()
    # create matplotlib figure
    fig, ax = plt.subplots(figsize=(18, 8))
    # slice to individual player
    idx = melt_df.player == player
    # get the maximum draft slot for given player for x-axis plotting purposes
    x_max = min(60, melt_df.query('player=="{0}"'.format(player))['duration'].max())
    # fit Kaplan-Meier survival model
    kmf.fit(melt_df.duration[idx], melt_df.observed[idx])
    # plot survival curve
    kmf.plot(ax=ax, legend=False)
    # set axes, titles. etc.
    ax.set(title='Survival Curve for {0}'.format(player),
           xlabel='Draft Slot',
           ylabel='Probability {0} is Still Available'.format(player.split()[-1]),
           xlim=(0,x_max+0.1),
           ylim=(-0.1,1.1))
    y_vals = ax.get_yticks()
    # format tickmarks
    ax.set_yticklabels(['{:3.0f}%'.format(x * 100) for x in y_vals])
    plt.xticks(range(0, int(x_max)+1), fontsize=10)
    ax.set_xticklabels(['{0}'.format(int(x)) for x in range(1, int(min(61, x_max+2)))])
    # either save figure or display
    if save:
        plt.savefig('../plots/players/{0}'.format(player.lower().replace(' ', '_')))
    else:
        plt.show()

def plot_Consensus_top_10(big_board_df, melt_df, save=False):
    """
    Plots the survival curve for the Consensus top-10 players, either displaying
    the output or saving to the `../plots` directory.

    Args:
        big_board_df (pandas DataFrame): the wide-form big board dataframe with
                                        player names and draft slots
        melt_df (pandas DataFrame): long-form big board dataframe with duration
                                    and censor columns
        save (boolean): Boolean of whether to write out the .png file in the
                        `../plots` director or display the image

    Returns:
        None
    """
    # consensus Top-10 Picks (By Average Ranking)
    top_10 = big_board_df['player'].to_list()[0:10]
    # create matplotlib figure with 10 subplots
    fig, axs = plt.subplots(nrows=10, ncols=1, sharey=True, sharex=False, figsize=(15,32))
    # loop through top 10 players plotting each to their respective subplot
    for player, ax in zip(top_10, axs.flatten()):
        # slice to individual player
        idx = melt_df.player == player
        # fit Kaplan-Meier survival model
        kmf = KaplanMeierFitter()
        kmf.fit(melt_df.duration[idx], melt_df.observed[idx])
        # plot individual player's survival curve
        kmf.plot(ax=ax, legend=False)
        # format xticks, etc.
        ax.set(title=player, xlabel='', xlim=(0,14), ylim=(-0.1, 1.1))
        y_vals = ax.get_yticks()
        ax.set_yticklabels(['{:3.0f}%'.format(x * 100) for x in y_vals])
        ax.set_xticks(range(0, 15))
        ax.set_xticklabels(['{0}'.format(int(x)) for x in range(1, 15)])
    # set title, axes, etc.
    fig.text(0.5, 0.001, "Draft Slot", ha="center", fontsize=18)
    fig.text(0.001, 0.5, "Probability Player is Still Available",
             va="center", rotation="vertical", fontsize=18)
    fig.suptitle("Survival Curve for Consensus Top-10 Picks",
                 fontsize=35)
    fig.tight_layout()
    fig.subplots_adjust(top=0.95)
    # either save figure or display
    if save:
        plt.savefig('../plots/top_10.png')
    else:
        plt.show()

def plot_Consensus_top_3(big_board_df, melt_df, save=False):
    """
    Plots the survival curve for the Consensus top-3 players, either displaying
    the output or saving to the `../plots` directory.

    Args:
        big_board_df (pandas DataFrame): the wide-form big board dataframe with
                                        player names and draft slots
        melt_df (pandas DataFrame): long-form big board dataframe with duration
                                    and censor columns
        save (boolean): Boolean of whether to write out the .png file in the
                        `../plots` director or display the image

    Returns:
        None
    """
    # consensus Top-3 Picks (By Average Ranking)
    top_3 = big_board_df['player'].to_list()[0:3]
    # get the maximum draft slot for given players for x-axis plotting purposes
    max_player = melt_df.query("player == @top_3")['duration'].max()
    # list of line styles for each player
    line_styles = ['-', '--', ':', '-.']
    # create matplotlib figure
    fig, ax = plt.subplots(figsize=(18, 8))
    # loop through top 3 players
    for player, ls in zip(top_3, line_styles):
        # slice to individual player
        idx = melt_df.player == player
        # fit Kaplan-Meier survival mode
        kmf = KaplanMeierFitter()
        kmf.fit(melt_df.duration[idx], melt_df.observed[idx])
        # plot player's survival curve
        kmf.plot(ax=ax, ci_show=False, label=player, ls=ls)
        # format title, axes, ticks
        ax.set(title='Survival Curve for Consensus Top-3 Picks',
               xlabel='Draft Slot',
               ylabel='Probability Player is Still Available',
               xlim=(0,max_player+1), ylim=(-0.1, 1.1))
        y_vals = ax.get_yticks()
        ax.set_yticklabels(['{:3.0f}%'.format(x * 100) for x in y_vals])
        plt.xticks(range(0, max_player+2))
        ax.set_xticklabels(['{0}'.format(int(x)) for x in range(1,max_player+2)])
    fig.tight_layout()
    fig.subplots_adjust(top=0.95)
    # either save figure or display
    if save:
        plt.savefig('../plots/top_3.png')
    else:
        plt.show()

def plot_multiple_players(player_list, melt_df):
    """
    Plots the survival curve for input player(s)

    Args:
        player_list (list): list of player names to plot survival curves
        melt_df (pandas DataFrame): long-form big board dataframe with duration
                                    and censor columns

    Returns:
        None
    """
    # create matplotlib figure
    fig, ax = plt.subplots(figsize=(18, 8))
    # list of line styles for each player
    line_styles = ['-', '--', ':', '-.']
    # get the maximum draft slot for given players for x-axis plotting purposes
    max_player = melt_df.query("player == @player_list")['duration'].max()
    # loop through players
    for player, ls in zip(player_list, line_styles):
        # slice to individual player
        idx = melt_df.player == player
        # fit Kaplan-Meier survival mode
        kmf = KaplanMeierFitter()
        kmf.fit(melt_df.duration[idx], melt_df.observed[idx])
        # plot player's survival curve
        kmf.plot(ax=ax, ci_show=False, label=player, ls=ls)
        # format title, axes, ticks
        ax.set(title='Survival Curve',
               xlabel='Draft Slot',
               ylabel='Probability Player is Still Available',
               xlim=(0, min(60, int(max_player))), ylim=(-0.1, 1.1))
        y_vals = ax.get_yticks()
        ax.set_yticklabels(['{:3.0f}%'.format(x * 100) for x in y_vals])
        plt.xticks(range(0, min(61, int(max_player)+2)), fontsize=10)
        ax.set_xticklabels(['{0}'.format(int(x)) for x in range(1, min(61, int(max_player)+2))])
    fig.tight_layout()
    fig.subplots_adjust(top=0.95)
    plt.show()

if __name__=='__main__':
    # Read in individual mock drafts
    babcock_hoops_df = pd.read_csv('../data/babcock_hoops.csv')
    bryan_kalbrosky_df = pd.read_csv('../data/bryan_kalbrosky.csv')
    chad_ford_df = pd.read_csv('../data/chad_ford.csv')
    chris_foresberg_df = pd.read_csv('../data/chris_foresberg.csv')
    chris_stone_df = pd.read_csv('../data/chris_stone.csv')
    danny_cunningham_df = pd.read_csv('../data/danny_cunningham.csv')
    gary_parrish_df = pd.read_csv('../data/gary_parrish.csv')
    james_ham_df = pd.read_csv('../data/james_ham.csv')
    jeff_goodman_df = pd.read_csv('../data/jeff_goodman.csv')
    jeremy_woo_df = pd.read_csv('../data/jeremy_woo.csv')
    john_hollinger_df = pd.read_csv('../data/john_hollinger.csv')
    jonathan_givony_df = pd.read_csv('../data/jonathan_givony.csv')
    jonathan_wasserman_df = pd.read_csv('../data/jonathan_wasserman.csv')
    kevin_oconnor_df = pd.read_csv('../data/kevin_oconnor.csv')
    krysten_peek_df = pd.read_csv('../data/krysten_peek.csv')
    kyle_boone_df = pd.read_csv('../data/kyle_boone.csv')
    nbadraftnet_df = pd.read_csv('../data/nbadraftnet.csv')
    netscouts_df = pd.read_csv('../data/netscouts.csv')
    ricky_odonnell_df = pd.read_csv('../data/ricky_odonnell.csv')
    sam_veceine_df = pd.read_csv('../data/sam_veceine.csv')
    scott_gleeson_df = pd.read_csv('../data/scott_gleeson.csv')
    tankathon_df = pd.read_csv('../data/tankathon.csv')

    # Pre-process individual mock drafts to match names
    mock_draft_list = [babcock_hoops_df, bryan_kalbrosky_df, chad_ford_df,
                       chris_foresberg_df, chris_stone_df, danny_cunningham_df,
                       gary_parrish_df, james_ham_df, jeff_goodman_df,
                       jeremy_woo_df, john_hollinger_df, jonathan_givony_df,
                       jonathan_wasserman_df, kevin_oconnor_df, krysten_peek_df,
                       kyle_boone_df, nbadraftnet_df, netscouts_df,
                       ricky_odonnell_df, sam_veceine_df, scott_gleeson_df,
                       tankathon_df]

    prospect_names = pd.read_csv('../data/prospects.csv')['player'].to_list()
    mock_draft_list = [pre_process_mocks(df, prospect_names) for df in mock_draft_list]

    # Join individual mock drafts using fuzzy name matching
    # Create an average rank for each player
    big_board_df = reduce(lambda x, y: pd.merge(x, y,
                                                on='fuzzy_name',
                                                how='outer',
                                                validate='one_to_one'),
                                                mock_draft_list)
    big_board_df = (big_board_df.rename({'fuzzy_name': 'player'},
                                        axis=1)
                                .assign(avg_rank=lambda x:
                                                x[[col for col in big_board_df.columns
                                                    if col != 'fuzzy_name']].mean(axis=1))
                                .sort_values(by='avg_rank')
                                .query("player.notnull()",
                                        engine='python'))
    big_board_df = big_board_df[['player'] + [ col for col in big_board_df.columns if col != 'player' ]]

    # Write out joined draft boards
    big_board_df.to_csv('../data/big_board.csv',
                        index=False)

    # Create observed flag to deal with censoring as not all mocks have ranked
    # up to draft slot 60: 1 if the player is in the mock draft, 0 (censored)
    # if not. Must be created before the nulls are filled below.
    rank_cols =[col for col in big_board_df.columns if col not in ['player', 'avg_rank']]
    mock_draft_name_list = [x.replace('_rank', '') for x in rank_cols]
    observed_col_names = ['{0}_observed'.format(mock_draft) for mock_draft in mock_draft_name_list]
    big_board_df[observed_col_names] = big_board_df[rank_cols].notnull().astype(int).to_numpy()
    observed_cols = [col for col in big_board_df.columns if '_observed' in col]

    # Fill nulls with the last draft slot of each respective mock draft
    # A player missing from a mock draft is only known to have not been
    # selected through that slot, so he is censored there (not one slot later)
    big_board_df[rank_cols] = big_board_df[rank_cols].fillna(big_board_df[rank_cols].max()).astype(int)

    # Transform wide big board into long form
    melt_1 = (pd.melt(big_board_df,
                        id_vars='player',
                        value_vars=rank_cols,
                        value_name='duration')
                 .assign(variable=lambda x: x['variable'].str.replace('_rank', '')))

    melt_2 = (pd.melt(big_board_df,
                        id_vars='player',
                        value_vars=observed_cols,
                        value_name='observed')
                  .assign(variable=lambda x: x['variable'].str.replace('_observed', '')))

    # Join duration and observed columns to create input dataframe for survival model
    melt_df = (melt_1.merge(melt_2,
                            on=['player', 'variable'],
                            how='inner'))

    # Write out Long Form Big Board
    melt_df.drop('variable', axis=1).to_csv('../data/big_board_long.csv',
                                            index=False)

    # Plot an individual player's survival curve
    # plot_player('Anthony Edwards', melt_df, save=False)

    # Save all player survival curves
    for player in melt_df['player'].unique():
        plot_player(player, melt_df, save=True)

    # Plot survival curves of consensus top ten picks
    plot_Consensus_top_10(big_board_df, melt_df, save=True)

    # Plot survival curves of Consensus top ten picks
    plot_Consensus_top_3(big_board_df, melt_df, save=True)

    # Plot survival curves of multiple players
    plot_multiple_players(['Theo Maledon', 'Malachi Flynn', 'Tyrell Terry'], melt_df)
